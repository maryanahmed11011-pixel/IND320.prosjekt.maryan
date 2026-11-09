"""Outliers (SPC/DCT) and anomalies (LOF) in ERA5 weather data.

The area comes from the global selector in the sidebar (app.py), the same
one that controls the reservoir data. Weather data is downloaded
automatically in the background and cached.
"""
import matplotlib.pyplot as plt
import streamlit as st

from analysis import lof_anomalies, spc_outliers
from utils import load_locations, load_weather

LABELS = {
    "temperature_2m": "Temperature (°C)",
    "precipitation": "Precipitation (mm)",
    "wind_speed_10m": "Wind speed (km/h)",
    "relative_humidity_2m": "Relative humidity (%)",
}

area = st.session_state.get("price_area", "NO3")
st.title(f"🌦️ Weather anomalies – {area}")
st.caption("Hourly ERA5 reanalysis from open-meteo, averaged over random "
           "points in the area. Change area in the sidebar.")

top_left, top_right = st.columns([2, 1])
with top_left:
    # Year is a local setting: it only matters on this page
    year = st.selectbox("Year", list(range(2025, 1999, -1)),
                        index=1)  # default 2024
    st.markdown(
        "Weather explains how the reservoirs fill: **heavy rain** adds water "
        "quickly, and **abrupt temperature changes** decide when snow melts. "
        "This page finds unusual hours in both."
    )
    st.caption("To keep within open-meteo's free limits, the app averages 20 "
               "ERA5 grid cells per area (the notebook uses all of them), so "
               "the numbers differ slightly from the notebook.")
with top_right:
    # Map of the 1000 random sample points for the selected area
    locs = load_locations()
    st.map(locs[locs["region"] == area], latitude="lat", longitude="lon",
           size=800, color="#3182bd", height=220)

weather = load_weather(area, year)
tab_spc, tab_lof = st.tabs(["Outliers (SPC)", "Anomalies (LOF)"])

with tab_spc:
    st.info(
        "**What you see:** the seasonal pattern is removed with a DCT "
        "high-pass filter, and hours outside median ± n robust SDs are "
        "marked red. For precipitation these are heavy-rain events, which "
        "often last several hours. A larger cut-off keeps more slow variation "
        "in the trend; more SDs give fewer outliers."
    )
    c1, c2, c3 = st.columns(3)
    var = c1.selectbox("Variable", list(LABELS), index=1,
                       format_func=LABELS.get, key="spc_var")
    cutoff = c2.slider("DCT cut-off (days)", 5, 120, 30)
    n_std = c3.slider("Number of robust SDs", 1.0, 6.0, 3.0, step=0.5)

    fig, summary, outliers = spc_outliers(
        weather[var], cutoff_days=cutoff, n_std=n_std, label=LABELS[var]
    )
    st.pyplot(fig)
    plt.close(fig)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Outliers", summary["n_outliers"])
    m2.metric("Share", f"{summary['share_%']} %")
    m3.metric("Above / below", f"{summary['n_above']} / {summary['n_below']}")
    m4.metric("Robust SD", summary["robust_sd"])
    with st.expander("Show outliers"):
        st.dataframe(outliers)

with tab_lof:
    st.info(
        "**What you see:** Local Outlier Factor compares each hour with its "
        "nearest neighbours in time and value. Red hours deviate clearly from "
        "the surrounding days, e.g. sudden cold spells or warm spikes. The "
        "proportion sets how many hours are marked."
    )
    c1, c2, c3 = st.columns(3)
    var = c1.selectbox("Variable", list(LABELS), index=0,
                       format_func=LABELS.get, key="lof_var")
    contamination = c2.slider("Proportion of outliers", 0.001, 0.10,
                              0.01, step=0.001, format="%.3f")
    n_neighbors = c3.slider("Number of neighbours", 5, 100, 20)

    fig, summary, anomalies = lof_anomalies(
        weather[var], contamination=contamination,
        n_neighbors=n_neighbors, label=LABELS[var]
    )
    st.pyplot(fig)
    plt.close(fig)

    m1, m2, m3 = st.columns(3)
    m1.metric("Anomalies", summary["n_anomalies"])
    m2.metric("Share", f"{summary['share_%']} %")
    m3.metric("Value range", f"{summary['min_value']} – {summary['max_value']}")
    with st.expander("Show anomalies"):
        st.dataframe(anomalies.sort_values("lof_score", ascending=False))
