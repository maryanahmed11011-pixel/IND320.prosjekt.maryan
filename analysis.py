"""Shared analysis functions used by the Streamlit app (part 3).

The same methods are developed and documented in the Jupyter Notebook.
Part 4: all plotting functions return dynamic Plotly figures (shown with
st.plotly_chart), styled by the "ind320" template in theme.py.
Plot titles leave out the parameters, since the sliders show them.
"""
import io
import time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from plotly.subplots import make_subplots
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

from theme import COLORS  # shared palette (also registers the Plotly template)

ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"


# ---------- Areas from NVE shapefiles (geo/ folder in the repo) ----------
# Downloaded from atlas.nve.no (the layer's table view, exported as a
# shapefile) and committed to the repository, so the notebook and the app
# read the same files and do not depend on NVE's map services.

# NVE regions mapped to the VASS areas in Magasinstatistikk
# (East = RØ + RS, West = RV, North = RM + RN, as in the assignment)
REGION_TO_VASS = {
    "RØ": "VASS1", "RS": "VASS1",
    "RV": "VASS2",
    "RM": "VASS3", "RN": "VASS3",
}


def _read_shapefile(folder):
    """Read the (single) shapefile in a folder, returned in WGS84."""
    import geopandas as gpd  # only needed here, so imported lazily

    folder = Path(folder)
    # Match the folder name without caring about upper/lower case:
    # Windows ignores case, but Linux (streamlit.io) does not
    matches = [p for p in folder.parent.iterdir()
               if p.is_dir() and p.name.lower() == folder.name.lower()]
    files = sorted(matches[0].rglob("*.shp")) if matches else []
    if not files:
        raise FileNotFoundError(f"No .shp file found in {folder}")
    # The NVE export is UTF-8 but has no .cpg file, so the encoding is
    # given explicitly (otherwise "RØ" is read wrongly and VASS1 loses RØ)
    gdf = gpd.read_file(files[0], encoding="utf-8")
    if gdf.crs is None:            # NVE exports use UTM 33N
        gdf = gdf.set_crs(epsg=25833)
    return gdf.to_crs(epsg=4326)


def _column(gdf, name):
    """Find a column by name, ignoring upper/lower case."""
    for col in gdf.columns:
        if col.lower() == name.lower():
            return gdf[col]
    raise KeyError(f"Column '{name}' not found, got {list(gdf.columns)}")


def load_areas(geo_dir="geo"):
    """Price areas (NO1–NO5) and VASS areas (VASS1–3) as one GeoDataFrame.

    Returns columns region and geometry, with one or more polygons per
    region (RØ + RS and RM + RN are merged later, when sampling).
    """
    geo_dir = Path(geo_dir)

    price = _read_shapefile(geo_dir / "budomrader")
    # Names come as "NO 1" ... -> "NO1"
    price["region"] = _column(price, "budomr").astype(str).str.replace(
        " ", "", regex=False)

    nve = _read_shapefile(geo_dir / "nve_region")
    nve["region"] = _column(nve, "REGION").map(REGION_TO_VASS)

    areas = pd.concat([price[["region", "geometry"]],
                       nve[["region", "geometry"]]], ignore_index=True)
    return areas.dropna(subset=["region"])


def sample_locations(areas, n=1000, seed=42):
    """Sample n random points inside each region -> region, lon, lat.

    Sampling is done in a metric CRS (UTM 33N), so points are uniform per
    km². Polygons are dissolved first, so RØ + RS and RM + RN become one
    area each.
    """
    import geopandas as gpd

    gdf_m = areas.dissolve(by="region").reset_index().to_crs(epsg=25833)
    frames = []
    for region, geom in zip(gdf_m["region"], gdf_m.geometry):
        pts = gpd.GeoSeries([geom], crs=gdf_m.crs).sample_points(n, rng=seed)
        pts = pts.explode(index_parts=False).to_crs(epsg=4326)
        frames.append(pd.DataFrame(
            {"region": region, "lon": pts.x.values, "lat": pts.y.values}
        ))
    return pd.concat(frames, ignore_index=True)
HOURLY_VARS = ["temperature_2m", "precipitation",
               "wind_speed_10m", "relative_humidity_2m"]

# Colours from the shared palette in theme.py
BLUE, RED, GREY = COLORS["primary"], COLORS["alert"], COLORS["neutral"]


# ---------- ERA5 download ----------

def snap_to_era5_grid(locs, res=0.25):
    """Round points to the ERA5 grid (~0.25 deg) and drop duplicates."""
    snapped = locs.assign(lat=(locs["lat"] / res).round() * res,
                          lon=(locs["lon"] / res).round() * res)
    return snapped.drop_duplicates(["lat", "lon"]).reset_index(drop=True)


def _get_with_retry(params, retries=5):
    """GET request that waits and retries if rate limited (HTTP 429)."""
    for attempt in range(retries):
        r = requests.get(ERA5_URL, params=params, timeout=120)
        if r.status_code == 429:
            if attempt < retries - 1:   # no point waiting after the last try
                time.sleep(60 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Too many retries against open-meteo")


def download_era5(locations, start, end, hourly=HOURLY_VARS,
                  batch_size=50, max_points=None, seed=42, retries=5):
    """Download hourly ERA5 data for a set of locations (columns lat, lon).

    Returns a long DataFrame: one row per location and hour.
    """
    locs = snap_to_era5_grid(locations)
    if locs.empty:
        raise ValueError("No locations given for the ERA5 download")
    if max_points and len(locs) > max_points:
        locs = locs.sample(max_points, random_state=seed)

    frames = []
    for i in range(0, len(locs), batch_size):
        batch = locs.iloc[i:i + batch_size]
        data = _get_with_retry({
            "latitude": ",".join(f"{v:.4f}" for v in batch["lat"]),
            "longitude": ",".join(f"{v:.4f}" for v in batch["lon"]),
            "start_date": start, "end_date": end,
            "hourly": ",".join(hourly), "models": "era5",
            "timezone": "GMT",
        }, retries=retries)
        data = [data] if isinstance(data, dict) else data
        for j, loc in enumerate(data):
            df = pd.DataFrame(loc["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            df["location_id"] = i + j
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


# ---------- Exchange rates from Norges Bank (part 4) ----------

NB_URL = "https://data.norges-bank.no/api/data/EXR/{freq}.{currencies}.NOK.SP"


def fetch_exchange_rates(currencies=("EUR", "USD"), start="2024-01-01",
                         end=None, freq="B"):
    """Exchange rates from Norges Bank's open data API (SDMX, no key).

    currencies : currency codes, e.g. ("EUR", "USD")
    start, end : dates as "YYYY-MM-DD" (end=None gives the newest data)
    freq       : "B" = business days, "M" = monthly, "A" = annual averages
    Returns a DataFrame with one column per currency, in NOK per unit of
    the currency (e.g. EUR = 11.7 means 1 EUR costs 11.7 NOK), indexed by
    date. Days without trading (weekends, holidays) are missing.
    """
    url = NB_URL.format(freq=freq, currencies="+".join(currencies))
    params = {"format": "csv", "startPeriod": start, "locale": "en"}
    if end:
        params["endPeriod"] = end
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    # Let pandas detect the separator, so a change from ; to , is handled
    raw = pd.read_csv(io.StringIO(r.text), sep=None, engine="python")
    cols = {c.upper(): c for c in raw.columns}
    missing = {"TIME_PERIOD", "BASE_CUR", "OBS_VALUE"} - set(cols)
    if missing:
        raise ValueError(f"Unexpected answer from Norges Bank, missing "
                         f"{missing}. Columns: {list(raw.columns)}")

    df = pd.DataFrame({
        "date": pd.to_datetime(raw[cols["TIME_PERIOD"]]),
        "currency": raw[cols["BASE_CUR"]],
        "nok": pd.to_numeric(raw[cols["OBS_VALUE"]], errors="coerce"),
    })
    # Some currencies are quoted per 100 units (e.g. JPY): UNIT_MULT = 2
    if "UNIT_MULT" in cols:
        mult = pd.to_numeric(raw[cols["UNIT_MULT"]], errors="coerce").fillna(0)
        df["nok"] = df["nok"] / 10 ** mult
    return (df.pivot(index="date", columns="currency", values="nok")
              .sort_index().rename_axis(columns=None))


# ---------- Outliers: SPC on DCT high-pass filtered data ----------

def spc_outliers(series, cutoff_days=30, n_std=3.0, label=None):
    """SPC outliers based on seasonally adjusted variations (DCT).

    Returns (fig, summary dict, outliers DataFrame).
    """
    x = series.to_numpy(dtype=float)

    # DCT coefficient k has period ~ 2n/k hours: keep low frequencies
    coefs = dct(x, norm="ortho")
    coefs[int(np.ceil(2 * len(x) / (cutoff_days * 24))):] = 0
    trend = idct(coefs, norm="ortho")
    satv = x - trend

    # Robust boundaries from the whole period, added back to the trend
    med = np.median(satv)
    robust_sd = 1.4826 * np.median(np.abs(satv - med))
    upper = trend + med + n_std * robust_sd
    lower = trend + med - n_std * robust_sd
    is_out = (x > upper) | (x < lower)

    fig = go.Figure()
    fig.add_scatter(x=series.index, y=x, mode="lines", name="Data",
                    line=dict(color=BLUE, width=1))
    fig.add_scatter(x=series.index, y=upper, mode="lines",
                    name=f"SPC limits (±{n_std} SD)",
                    line=dict(color=GREY, width=1, dash="dash"))
    fig.add_scatter(x=series.index, y=lower, mode="lines", showlegend=False,
                    name="Lower limit",
                    line=dict(color=GREY, width=1, dash="dash"))
    fig.add_scatter(x=series.index[is_out], y=x[is_out], mode="markers",
                    name="Outliers", marker=dict(color=RED, size=5))
    fig.update_layout(title=f"SPC outliers – {label}", yaxis_title=label,
                      height=420, hovermode="closest")

    outliers = pd.DataFrame({"value": x[is_out], "lower": lower[is_out],
                             "upper": upper[is_out]},
                            index=series.index[is_out])
    summary = {
        "n_outliers": int(is_out.sum()),
        "share_%": round(float(100 * is_out.mean()), 2),
        "n_above": int((x > upper).sum()),
        "n_below": int((x < lower).sum()),
        "robust_sd": round(float(robust_sd), 3),
    }
    return fig, summary, outliers


# ---------- Anomalies: Local Outlier Factor ----------

def lof_anomalies(series, contamination=0.01, n_neighbors=20,
                  time_scale=24, label=None):
    """LOF anomalies fitted on (time in days, value).

    Returns (fig, summary dict, anomalies DataFrame).
    """
    x = series.to_numpy(dtype=float)
    t = (series.index - series.index[0]) / pd.Timedelta(hours=time_scale)
    features = np.column_stack([np.asarray(t, dtype=float), x])

    lof = LocalOutlierFactor(n_neighbors=n_neighbors,
                             contamination=contamination)
    is_anom = lof.fit_predict(features) == -1
    scores = -lof.negative_outlier_factor_

    fig = go.Figure()
    fig.add_scatter(x=series.index, y=x, mode="lines", name="Data",
                    line=dict(color=BLUE, width=1))
    fig.add_scatter(x=series.index[is_anom], y=x[is_anom], mode="markers",
                    name=f"LOF anomalies ({contamination:.1%})",
                    marker=dict(color=RED, size=6),
                    customdata=scores[is_anom],
                    hovertemplate="%{x}<br>%{y:.2f}<br>"
                                  "LOF score %{customdata:.2f}<extra></extra>")
    fig.update_layout(title=f"LOF anomalies – {label}", yaxis_title=label,
                      height=420, hovermode="closest")

    anomalies = pd.DataFrame({"value": x[is_anom],
                              "lof_score": scores[is_anom]},
                             index=series.index[is_anom])
    summary = {
        "n_anomalies": int(is_anom.sum()),
        "share_%": round(float(100 * is_anom.mean()), 2),
        "min_value": round(float(x[is_anom].min()), 2),
        "max_value": round(float(x[is_anom].max()), 2),
    }
    return fig, summary, anomalies


# ---------- STL and spectrogram ----------

def stl_decompose(series, period=52, seasonal=13, trend=105,
                  robust=False, label=None):
    """STL decomposition of a weekly series. Returns a Plotly figure."""
    fit = STL(series, period=period, seasonal=seasonal,
              trend=trend, robust=robust).fit()

    parts = [(series, "Observed"), (fit.trend, "Trend"),
             (fit.seasonal, "Seasonal"), (fit.resid, "Residual")]
    # Four panels with a shared time axis (zooming one zooms all)
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03)
    for row, (data, name) in enumerate(parts, start=1):
        fig.add_scatter(x=data.index, y=data, mode="lines", name=name,
                        line=dict(color=BLUE, width=1.2), row=row, col=1)
        fig.update_yaxes(title_text=name, row=row, col=1)
    fig.update_layout(title=f"STL – {label}", height=650, showlegend=False)
    return fig


def plot_spectrogram(series, window_length=104, overlap=78,
                     max_freq=6, label=None):
    """Spectrogram of a weekly series (cycles per year). Returns a Plotly figure."""
    freqs, times, power = spectrogram(
        series.to_numpy(dtype=float), fs=52, nperseg=window_length,
        noverlap=overlap, detrend="constant",
    )
    dates = series.index[0] + pd.to_timedelta(times * 365.25, unit="D")

    keep = freqs <= max_freq  # only show the frequencies of interest
    fig = go.Figure(go.Heatmap(
        x=dates, y=freqs[keep], z=10 * np.log10(power[keep] + 1e-12),
        colorscale="YlGnBu_r",  # blue palette, bright = strong cycle
        colorbar=dict(title="Power (dB)"),
        hovertemplate="%{x|%Y-%m}<br>%{y:.2f} cycles/year<br>"
                      "%{z:.1f} dB<extra></extra>",
    ))
    fig.update_layout(title=f"Spectrogram – {label}",
                      yaxis_title="Frequency (cycles per year)",
                      height=420, hovermode="closest")
    return fig
