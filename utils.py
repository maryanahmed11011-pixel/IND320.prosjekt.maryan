"""Shared helper functions for all pages in the Streamlit app.

Data is loaded in one place only, so all pages use the same loading code,
the same English column names and the same caching.

Part 2: the CSV file was replaced by a direct connection to NVE's
Magasinstatistikk API, and cross-border flows are read from MongoDB.
Part 3: weather data from open-meteo (ERA5) for price areas and VASS
areas. The areas are read from the NVE shapefiles in the geo/ folder of
the repository, and 1000 random points are sampled per area.
"""
import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from pymongo import MongoClient

from analysis import (HOURLY_VARS, area_geojson, daily_to_weekly,
                      download_era5, fetch_exchange_rates, forecast_filling,
                      hourly_to_daily, load_areas, sample_locations)

# geo/ folder next to this file, so the path works locally and on streamlit.io
GEO_DIR = Path(__file__).resolve().parent / "geo"

# NVE's open Magasinstatistikk API (no key needed)
API_URL = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

# Original (Norwegian) column names -> English, descriptive names
RENAME = {
    "dato_Id": "date",
    "omrType": "area_type",
    "omrnr": "area_number",
    "iso_aar": "iso_year",
    "iso_uke": "iso_week",
    "fyllingsgrad": "filling_degree",
    "kapasitet_TWh": "capacity_TWh",
    "fylling_TWh": "filling_TWh",
    "neste_Publiseringsdato": "next_publication_date",
    "fyllingsgrad_forrige_uke": "filling_degree_prev_week",
    "endring_fyllingsgrad": "filling_degree_change",
}

# Measures that can be selected in the plots. area_number, iso_year and
# iso_week are not included: areas are shown as lines and year/week is time.
MEASURE_COLS = [
    "filling_degree",
    "capacity_TWh",
    "filling_TWh",
    "filling_degree_prev_week",
    "filling_degree_change",
]

# Unit for each measure, used as axis label in the plots
UNITS = {
    "filling_degree": "Filling degree (share, 0-1)",
    "capacity_TWh": "Capacity (TWh)",
    "filling_TWh": "Stored energy (TWh)",
    "filling_degree_prev_week": "Filling degree last week (share, 0-1)",
    "filling_degree_change": "Weekly change in filling degree",
}

# The three area types in the API, with labels for the radio buttons
AREA_TYPES = {
    "NO": "NO – whole of Norway",
    "EL": "EL – price areas NO1–NO5",
    "VASS": "VASS – river system regions 1–3",
}

# Areas in the global selector (app.py): price areas and VASS areas
AREAS = {
    "NO1": "NO1 – East (price area)",
    "NO2": "NO2 – South-west (price area)",
    "NO3": "NO3 – Central (price area)",
    "NO4": "NO4 – North (price area)",
    "NO5": "NO5 – West (price area)",
    "VASS1": "VASS1 – East (precipitation area)",
    "VASS2": "VASS2 – West (precipitation area)",
    "VASS3": "VASS3 – North (precipitation area)",
}


def area_label(area_type: str, number: int) -> str:
    """Readable name of an area, e.g. 'NO2' or 'VASS3'."""
    if area_type == "NO":
        return "Norway"
    if area_type == "EL":
        return f"NO{number}"
    return f"VASS{number}"


# ---------- Error handling (bonus task, part 4) ----------
# Names of the data sources, used in the error messages
NVE = "the NVE Magasinstatistikk API"
MONGO = "the MongoDB database"
METEO = "open-meteo (ERA5)"
NORGES_BANK = "Norges Bank"


def stop_with_error(source: str, err: Exception,
                    hint: str = "Please try again in a minute.") -> None:
    """Show a short, readable error message instead of a traceback, with
    the technical details folded away, and stop the page."""
    st.error(f"**Could not load data from {source}.** {hint}", icon="⚠️")
    with st.expander("Technical details"):
        st.code(f"{type(err).__name__}: {err}")
    st.stop()


def load_or_stop(source: str, func, *args, hint: str | None = None, **kwargs):
    """Call a data loading function; on any error, show a useful message
    (stop_with_error) instead of crashing the page."""
    try:
        return func(*args, **kwargs)
    except Exception as err:  # connection, timeout, HTTP or data errors
        stop_with_error(source, err, hint or "Please try again in a minute.")


def mongo_db():
    """MongoDB database for the app.

    The connection string is read from st.secrets (locally:
    .streamlit/secrets.toml, on streamlit.io: Secrets in the app settings),
    so it never ends up on GitHub. A short server timeout makes the page
    show an error after 5 seconds instead of waiting for 30.
    """
    try:
        uri = st.secrets["mongo"]["uri"]
    except Exception as err:  # no secrets file or no [mongo] section
        raise RuntimeError("MongoDB is not configured: add [mongo] uri to "
                           ".streamlit/secrets.toml") from err
    return MongoClient(uri, serverSelectionTimeoutMS=5000)["ind320"]


# ---------- Reservoir data (NVE API) ----------

@st.cache_data(ttl=3600)  # the API is called at most once an hour
def fetch_reservoirs() -> pd.DataFrame:
    """Fetch all reservoir statistics from the NVE API, with English names."""
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    df = pd.DataFrame(response.json()).rename(columns=RENAME)
    # Check the answer before using it, so a changed or empty API response
    # gives a clear message instead of a KeyError somewhere else
    missing = {"date", "area_type", "area_number", "filling_degree"} - set(df.columns)
    if df.empty or missing:
        raise ValueError(f"Unexpected answer from the NVE API (missing: {missing})")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    # Month column (e.g. "1995-01") used to select periods in the app
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df


def load_data(area_type: str = "NO", start_month: str | None = None,
              end_month: str | None = None) -> pd.DataFrame:
    """Data for one area type (NO, EL or VASS), optionally for a period.

    The result is sorted by area and date. Without a period, all data
    is returned.
    """
    df = fetch_reservoirs()
    df = df[df["area_type"] == area_type]
    if start_month is not None and end_month is not None:
        # Months have the format "YYYY-MM", so text comparison sorts correctly
        df = df[(df["month"] >= start_month) & (df["month"] <= end_month)]
    return df.sort_values(["area_number", "date"]).reset_index(drop=True)


def filling_series(region: str) -> pd.Series:
    """Weekly filling degree for one area, e.g. 'NO3' or 'VASS2'."""
    area_type = "VASS" if region.startswith("VASS") else "EL"
    df = load_data(area_type)
    number = int(region[-1])
    series = (df[df["area_number"] == number]
              .set_index("date")["filling_degree"].sort_index())
    # STL and the spectrogram need a complete weekly series: single missing
    # weeks are interpolated, longer gaps at the ends are dropped
    return series.interpolate(limit=4, limit_area="inside").dropna()


# ---------- Cross-border flows (MongoDB) ----------

@st.cache_data(ttl=3600)
def load_flows() -> pd.DataFrame:
    """Daily cross-border flows, stored in MongoDB from the notebook."""
    docs = list(mongo_db()["flows_daily"].find({}, {"_id": 0}))
    if not docs:
        raise ValueError("The collection flows_daily in MongoDB is empty")
    df = pd.DataFrame(docs).dropna(subset=["date", "energy_mwh"])
    df["date"] = pd.to_datetime(df["date"])
    # The days were summed in UTC (part 2), so the first local hour of
    # 2024 is stored as a one-hour "day" on 2023-12-31 (see the time zone
    # section in the part 4 notebook). It is left out here.
    df = df[df["date"] >= "2024-01-01"]
    return df.sort_values(["connection", "direction", "date"]).reset_index(drop=True)


# ---------- Weather data (open-meteo ERA5) ----------

@st.cache_data(show_spinner="Sampling points in the NVE areas ...")
def load_locations() -> pd.DataFrame:
    """1000 random points per area, sampled from the NVE shapefiles in geo/.

    Same function and seed as in the notebook, so the points are the same.
    """
    return sample_locations(load_areas(GEO_DIR), n=1000, seed=42)


@st.cache_data(show_spinner="Downloading ERA5 weather data ...")
def load_weather(region: str, year: int,
                 max_points: int = 20) -> pd.DataFrame:
    """Hourly ERA5 data averaged over the sampled points in a region.

    max_points limits the number of ERA5 grid cells to stay within
    open-meteo's free rate limits. Results are cached on the server,
    so each region/year is only downloaded once.
    """
    locs = load_locations()
    locs = locs[locs["region"] == region]
    if locs.empty:
        raise ValueError(f"No sampled locations for {region}")
    # ERA5 in open-meteo lags about five days behind today, so the end
    # date of the current year is moved back to the newest available day
    end = min(pd.Timestamp(f"{year}-12-31"),
              pd.Timestamp.today().normalize() - pd.Timedelta(days=6))
    if end < pd.Timestamp(f"{year}-01-01"):
        raise ValueError(f"No ERA5 data available yet for {year}")
    # Few retries in the app, so a rate limit gives an error message
    # quickly instead of a page that spins for many minutes
    df = download_era5(locs, f"{year}-01-01", f"{end:%Y-%m-%d}",
                       max_points=max_points, retries=2)
    hourly = df.groupby("time")[HOURLY_VARS].mean()
    # Missing values: short gaps (up to 6 hours) are interpolated, longer
    # gaps are dropped. The number is kept in attrs, so pages can show it.
    missing = int(hourly.isna().any(axis=1).sum())
    hourly = hourly.interpolate(limit=6, limit_area="inside").dropna()
    if hourly.empty:
        raise ValueError(f"No weather data returned for {region} in {year}")
    hourly.attrs["missing_hours"] = missing
    return hourly


@st.cache_data(show_spinner="Aggregating weather data to weeks ...")
def load_weather_weekly(region: str, year: int,
                        max_points: int = 5) -> pd.DataFrame:
    """Weekly weather for a region on the Magasinstatistikk week grid.

    Hourly UTC data -> local days -> weeks ending on Sunday (see
    hourly_to_daily and daily_to_weekly in analysis.py). Precipitation is
    summed, the other variables are averaged. The map uses few points per
    area (max_points=5) to stay within open-meteo's free limits.
    """
    hourly = load_weather(region, year, max_points=max_points)
    return daily_to_weekly(hourly_to_daily(hourly))


@st.cache_data(show_spinner="Combining weekly weather data over the years ...")
def load_weather_weekly_years(region: str, start_year: int, end_year: int,
                              max_points: int = 5) -> pd.DataFrame:
    """Weekly weather for a region over several years (correlation and
    forecasting pages). The hourly data is combined before aggregating,
    so the weeks at New Year are not split in two."""
    hourly = pd.concat([load_weather(region, y, max_points=max_points)
                        for y in range(start_year, end_year + 1)])
    hourly = hourly[~hourly.index.duplicated()].sort_index()
    return daily_to_weekly(hourly_to_daily(hourly))


@st.cache_data(ttl=6 * 3600, show_spinner="Loading exchange rates from Norges Bank ...")
def load_exchange_rates(start_year: int) -> pd.DataFrame:
    """EUR and USD (NOK per unit) per business day from Norges Bank.
    Cached for six hours, since new rates are published once a day."""
    return fetch_exchange_rates(("EUR", "USD"), start=f"{start_year}-01-01")


def load_exchange_rates_weekly(start_year: int) -> pd.DataFrame:
    """EUR and USD (NOK per unit) as weekly means on the Sunday weeks."""
    return daily_to_weekly(load_exchange_rates(start_year))


@st.cache_data(show_spinner="Training the model and forecasting ...")
def cached_forecast(y: pd.Series, X, exog: tuple, end, settings: tuple):
    """forecast_filling with caching, so the same forecast is not trained
    twice (settings is a tuple of (name, value) pairs, which can be hashed)."""
    return forecast_filling(y, X=X, exog=list(exog), end=end, **dict(settings))


# ---------- Map areas (GeoJSON) ----------

@st.cache_data
def load_geojson(layer: str) -> dict:
    """GeoJSON for "price" (NO1–NO5) or "water" (VASS1–3) areas.

    Reads geo/price_areas.geojson or geo/water_areas.geojson, which the
    part 4 notebook converts from the NVE shapefiles. If a file is
    missing, the GeoJSON is built from the shapefiles instead.
    """
    path = GEO_DIR / f"{layer}_areas.geojson"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return area_geojson(load_areas(GEO_DIR), layer)
