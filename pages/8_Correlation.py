"""Sliding window correlation: weather vs. reservoirs (part 4).

Streamlit/Plotly version of the lecture's lagged_correlation_plot: a
weather property (ERA5) is compared with a representative variable from
Magasinstatistikk for the area chosen in the sidebar (or on the map).

- lag: the weather is shifted forward, so the reservoir in week t is
  compared with the weather `lag` weeks earlier.
- window: number of weeks in each correlation (centred).
- centre: the week whose window is highlighted in the two upper panels.

Both series are on the same weekly grid (weeks ending on Sunday, local
time), using the helpers from the time zone section of the notebook.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analysis import correlation_by_lag, lagged_correlation, sliding_window_correlation
from theme import COLORS
from utils import AREAS, NVE, load_data, load_or_stop, load_weather_weekly_years

WEATHER = {
    "temperature_2m": "Temperature (°C, weekly mean)",
    "precipitation": "Precipitation (mm, weekly sum)",
    "wind_speed_10m": "Wind speed (km/h, weekly mean)",
    "relative_humidity_2m": "Relative humidity (%, weekly mean)",
}
RESERVOIR = {
    "change": "Weekly change in filling degree (pp)",
    "filling": "Filling degree (%)",
}
HIGHLIGHT = COLORS["alert"]  # red, as for outliers

area = st.session_state.get("price_area", "NO3")
st.title(f"🔗 Weather vs. reservoirs – {area}")
st.caption("Sliding window correlation between a weather property and the "
           "reservoirs in the area chosen in the sidebar or on the map.")

st.info(
    "**What you see:** the upper panels show the two weekly series, with "
    "the chosen window in red (the weather window is moved back by the "
    "lag). The lower panel shows the correlation in a window around every "
    "week, so you can see when the relationship is strong, weak or changes "
    "sign. **Lag** = how many weeks earlier the weather is taken. The "
    "*weekly change* in filling is usually more informative than the level, "
    "since both the level and the weather follow the seasons."
)

# ---------- Controls ----------
c1, c2, c3 = st.columns(3)
weather_var = c1.selectbox("Weather property", list(WEATHER),
                           format_func=WEATHER.get, key="corr_weather")
res_var = c2.selectbox("Reservoir variable", list(RESERVOIR),
                       format_func=RESERVOIR.get, key="corr_reservoir")
this_year = pd.Timestamp.today().year
start_year, end_year = c3.select_slider(
    "Years", options=list(range(2000, this_year + 1)),
    value=(this_year - 6, this_year - 1), key="corr_years")

s1, s2 = st.columns(2)
lag = s1.slider("Lag (weeks the weather is taken earlier)", 0, 26, 0,
                key="corr_lag")
window = s2.slider("Window length (weeks)", 4, 104, 26, step=2,
                   key="corr_window")

# ---------- Data on the same weekly grid ----------
area_type = "VASS" if area.startswith("VASS") else "EL"
number = int(area.replace("VASS", "").replace("NO", ""))
res = load_or_stop(NVE, load_data, area_type)
res = (res[res["area_number"] == number].set_index("date")["filling_degree"]
       .sort_index() * 100)
y = res.diff() if res_var == "change" else res
y = y.rename(RESERVOIR[res_var])

try:
    weather = load_weather_weekly_years(area, start_year, end_year)
except Exception as err:  # e.g. rate limit (HTTP 429) from open-meteo
    st.error("Could not download weather data from open-meteo. The free API "
             "may be rate limited – please try again in a minute, or choose "
             f"fewer years.\n\nDetails: {err}")
    st.stop()
x = weather[weather_var].rename(WEATHER[weather_var])

# Keep the weeks that both series have (the lagged weather may reach back
# before the first week, so the lag is applied on the full weather series)
data = pd.concat([y, x], axis=1, join="inner").dropna()
if len(data) < window + lag + 2:
    st.warning("Too few weeks for this window and lag. Choose more years, "
               "a shorter window or a smaller lag.")
    st.stop()
y, x = data.iloc[:, 0], data.iloc[:, 1]
swc = sliding_window_correlation(y, x, window=window, lag=lag)

# Centre of the highlighted window (a week on the reservoir axis)
weeks = list(data.index)
first, last = window // 2 + lag, len(weeks) - window // 2 - 1
centre = st.select_slider(
    "Centre of the highlighted window", options=weeks[first:last + 1],
    value=weeks[(first + last) // 2],
    format_func=lambda d: f"{d:%d %b %Y}", key=f"corr_centre_{window}_{lag}")
i = weeks.index(centre)
res_win = data.index[i - window // 2: i + window // 2]
wea_win = data.index[i - window // 2 - lag: i + window // 2 - lag]

# ---------- Key numbers ----------
m1, m2, m3 = st.columns(3)
m1.metric(f"Correlation, whole period (lag {lag})",
          f"{lagged_correlation(y, x, lag):.2f}")
m2.metric(f"Correlation in window around {centre:%d %b %Y}",
          f"{swc.loc[centre]:.2f}" if pd.notna(swc.loc[centre]) else "–")
m3.metric("Weeks used", f"{len(data)}")

# ---------- Three panels, as in the lecture ----------
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                    row_heights=[0.32, 0.32, 0.36],
                    subplot_titles=(y.name, f"{x.name} (window moved back "
                                    f"{lag} weeks)", "Sliding window correlation"))
fig.add_scatter(x=y.index, y=y, mode="lines", name=y.name,
                line=dict(color=COLORS["primary"], width=1.3), row=1, col=1)
fig.add_scatter(x=res_win, y=y.loc[res_win], mode="lines", name="Window",
                line=dict(color=HIGHLIGHT, width=2), row=1, col=1)
fig.add_scatter(x=x.index, y=x, mode="lines", name=x.name,
                line=dict(color=COLORS["dark"], width=1.3), row=2, col=1)
fig.add_scatter(x=wea_win, y=x.loc[wea_win], mode="lines",
                name="Window (lagged)", line=dict(color=HIGHLIGHT, width=2),
                row=2, col=1)
fig.add_scatter(x=swc.index, y=swc, mode="lines", name="Correlation",
                line=dict(color=COLORS["primary"], width=1.6), row=3, col=1)
if pd.notna(swc.loc[centre]):
    fig.add_scatter(x=[centre], y=[swc.loc[centre]], mode="markers",
                    name="Centre", marker=dict(color=HIGHLIGHT, size=9),
                    row=3, col=1)
fig.add_hline(y=0, line=dict(color="grey", dash="dot", width=1), row=3, col=1)
fig.update_yaxes(range=[-1, 1], title_text="r", row=3, col=1)
fig.update_layout(height=720, showlegend=False, hovermode="x unified",
                  margin=dict(t=50))
st.plotly_chart(fig, theme=None)

# ---------- Which lag fits best? ----------
with st.expander("Correlation for every lag (whole period)", expanded=True):
    by_lag = correlation_by_lag(y, x, max_lag=26)
    if by_lag.isna().all():  # e.g. a constant series
        st.info("The correlation cannot be computed for this selection.")
        st.stop()
    best = by_lag.abs().idxmax()
    bar = go.Figure(go.Bar(
        x=by_lag.index, y=by_lag.values,
        marker_color=[HIGHLIGHT if lg == lag else COLORS["primary"]
                      for lg in by_lag.index],
        hovertemplate="Lag %{x} weeks: r = %{y:.2f}<extra></extra>"))
    bar.update_layout(height=280, xaxis_title="Lag (weeks)",
                      yaxis=dict(title="r", range=[-1, 1]),
                      hovermode="closest", margin=dict(t=20))
    st.plotly_chart(bar, theme=None)
    st.caption(f"Strongest relationship at lag {best} weeks "
               f"(r = {by_lag[best]:.2f}). The chosen lag is shown in red.")

with st.expander("About the data"):
    st.markdown(
        f"- **Reservoirs:** NVE Magasinstatistikk for {AREAS.get(area, area)}, "
        "weekly, dated on the Sunday that ends the ISO week. The weekly "
        "change is the difference from the week before (percentage points).\n"
        "- **Weather:** ERA5 from open-meteo, averaged over 5 random points "
        "in the area, converted from UTC to local days and aggregated to the "
        "same weeks (precipitation summed, the rest averaged).\n"
        "- **Correlation:** Pearson's r. A correlation does not show cause "
        "and effect, and strong seasonal patterns can give high r on their own."
    )
