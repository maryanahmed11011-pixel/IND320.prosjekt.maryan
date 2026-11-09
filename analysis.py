"""Shared analysis functions used by the Streamlit app (part 3).

The same methods are developed and documented in the Jupyter Notebook.
All plotting functions return matplotlib figures (shown with st.pyplot).
Plot titles leave out the parameters, since the sliders show them.
"""
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

from theme import COLORS  # shared palette (also applies the plot style)

ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
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
            time.sleep(60 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Too many retries against open-meteo")


def download_era5(locations, start, end, hourly=HOURLY_VARS,
                  batch_size=50, max_points=None, seed=42):
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
        })
        data = [data] if isinstance(data, dict) else data
        for j, loc in enumerate(data):
            df = pd.DataFrame(loc["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            df["location_id"] = i + j
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


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

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(series.index, x, lw=0.6, color=BLUE, label="Data")
    ax.plot(series.index, upper, "--", lw=1, color=GREY,
            label=f"SPC limits (±{n_std} SD)")
    ax.plot(series.index, lower, "--", lw=1, color=GREY)
    ax.scatter(series.index[is_out], x[is_out], s=8, color=RED,
               zorder=3, label="Outliers")
    ax.set(ylabel=label, title=f"SPC outliers – {label}")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right")
    fig.tight_layout()

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

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(series.index, x, lw=0.6, color=BLUE, label="Data")
    ax.scatter(series.index[is_anom], x[is_anom], s=10, color=RED,
               zorder=3, label=f"LOF anomalies ({contamination:.1%})")
    ax.set(ylabel=label, title=f"LOF anomalies – {label}")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right")
    fig.tight_layout()

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
    """STL decomposition of a weekly series. Returns a figure."""
    fit = STL(series, period=period, seasonal=seasonal,
              trend=trend, robust=robust).fit()

    fig, axes = plt.subplots(4, 1, figsize=(12, 6.5), sharex=True)
    parts = [(series, "Observed"), (fit.trend, "Trend"),
             (fit.seasonal, "Seasonal"), (fit.resid, "Residual")]
    for ax, (data, name) in zip(axes, parts):
        ax.plot(data.index, data, lw=0.8, color=BLUE)
        ax.set_ylabel(name)
        ax.grid(True, linestyle="--", alpha=0.4)
    axes[0].set_title(f"STL – {label}")
    fig.tight_layout()
    return fig


def plot_spectrogram(series, window_length=104, overlap=78,
                     max_freq=6, label=None):
    """Spectrogram of a weekly series (cycles per year). Returns a figure."""
    freqs, times, power = spectrogram(
        series.to_numpy(dtype=float), fs=52, nperseg=window_length,
        noverlap=overlap, detrend="constant",
    )
    dates = series.index[0] + pd.to_timedelta(times * 365.25, unit="D")

    fig, ax = plt.subplots(figsize=(12, 4))
    mesh = ax.pcolormesh(dates, freqs, 10 * np.log10(power + 1e-12),
                         shading="auto", cmap="YlGnBu_r")  # blue palette
    fig.colorbar(mesh, ax=ax, label="Power (dB)")
    ax.set(ylabel="Frequency (cycles per year)", ylim=(0, max_freq),
           title=f"Spectrogram – {label}")
    fig.tight_layout()
    return fig
