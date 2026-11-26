"""Forecast of reservoir filling with River's SNARIMAX (part 4).

- All model parameters and the exogenous variables can be chosen.
- The training period ends at the week chosen on the map (shared via
  st.session_state["map_week"]), and changing it here also moves the map.
- The forecast is dynamic (each step builds on the previous forecast steps)
  and is shown as a Plotly animation, one week at a time.
- The defaults are the best setting from the tests in the part 4 notebook
  (FORECAST_DEFAULTS in analysis.py).
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import FORECAST_DEFAULTS, seasonal_naive
from insights import csv_download, weekly_normal
from theme import COLORS
from utils import (AREAS, NVE, cached_forecast, load_data, load_exchange_rates_weekly,
                   load_or_stop, load_weather_weekly_years)

EXOG = {
    "temperature_2m": "Temperature (weekly mean)",
    "precipitation": "Precipitation (weekly sum)",
    "wind_speed_10m": "Wind speed (weekly mean)",
    "relative_humidity_2m": "Relative humidity (weekly mean)",
    "EUR": "EUR exchange rate (Norges Bank)",
    "USD": "USD exchange rate (Norges Bank)",
}
WEATHER_FIRST_YEAR = 2000  # weather data is downloaded from 2000
D = FORECAST_DEFAULTS

area = st.session_state.get("price_area", "NO3")
st.title(f"🔮 Reservoir forecast – {area}")
st.caption(f"{AREAS.get(area, area)} · River SNARIMAX, weekly data from NVE "
           "Magasinstatistikk. The defaults are the best setting from the "
           "tests in the notebook.")

# ---------- Target: weekly filling degree (%) ----------
area_type = "VASS" if area.startswith("VASS") else "EL"
number = int(area.replace("VASS", "").replace("NO", ""))
fill = load_or_stop(NVE, load_data, area_type)
y = (fill[fill["area_number"] == number].set_index("date")["filling_degree"]
     .sort_index() * 100)
weeks = list(y.index)

# ---------- Time frame (synced with the map) ----------
st.subheader("Time frame")
t1, t2, t3 = st.columns([2, 1, 1])
default_end = pd.Timestamp(st.session_state.get("map_week", weeks[-1]))
if default_end not in weeks:
    default_end = weeks[-1]
end = t1.select_slider(
    "Last week of training (forecast starts the week after)",
    options=weeks[260:], value=default_end,
    format_func=lambda d: f"Week {d.isocalendar().week} · {d:%d %b %Y}",
    help="The same week as chosen on the map. Changing it here also "
         "changes the week on the map.")
st.session_state["map_week"] = end  # keep the map in sync
history_weeks = t2.slider("History (weeks)", 104, 1040, D["history_weeks"],
                          step=52, help="How many weeks the model learns from.")
horizon = t3.slider("Horizon (weeks)", 4, 52, D["horizon"], step=1)

train_start = end - pd.Timedelta(weeks=history_weeks)
st.caption(f"Training: {max(train_start, weeks[0]):%d %b %Y} – {end:%d %b %Y}"
           f" · Forecast: {end + pd.Timedelta(weeks=1):%d %b %Y} – "
           f"{end + pd.Timedelta(weeks=horizon):%d %b %Y}")

# ---------- Model ----------
with st.expander("Model parameters (SNARIMAX)", expanded=False):
    m1, m2, m3, m4 = st.columns(4)
    p = m1.number_input("p (AR order)", 0, 8, D["p"])
    d = m2.number_input("d (differencing)", 0, 2, D["d"])
    q = m3.number_input("q (MA order)", 0, 4, D["q"])
    lr = m4.select_slider("Learning rate", [0.001, 0.003, 0.01, 0.03, 0.1],
                          value=D["learning_rate"])
    s1, s2, s3, s4 = st.columns(4)
    m = s1.number_input("m (season length, weeks)", 1, 52, D["m"])
    sp = s2.number_input("sp (seasonal AR)", 0, 2, D["sp"])
    sd = s3.number_input("sd (seasonal differencing)", 0, 1, D["sd"])
    sq = s4.number_input("sq (seasonal MA)", 0, 2, D["sq"])
    st.caption("Best in the notebook tests: p=2, d=0, q=0, m=52, sd=1. "
               "Without seasonal terms the model only continues the recent "
               "trend.")

# ---------- Exogenous variables ----------
e1, e2 = st.columns([3, 1])
exog = e1.multiselect("Exogenous variables", list(EXOG), format_func=EXOG.get,
                      default=[], help="None improved the forecast for NO3 "
                      "in the notebook tests, but they can be tried here.")
future = e2.radio("Future values of the exogenous variables",
                  ["climatology", "observed"],
                  format_func={"climatology": "Weekly averages",
                               "observed": "Observed (past only)"}.get,
                  help="The future weather is unknown when forecasting, so "
                       "the averages for the same weeks are used. "
                       "'Observed' uses the real values, which only exist "
                       "when the forecast lies in the past.")

X = None
if exog:
    if train_start.year < WEATHER_FIRST_YEAR and any(v not in ("EUR", "USD") for v in exog):
        st.info(f"Weather data starts in {WEATHER_FIRST_YEAR}, so the "
                "training period is shortened to the weeks with data.")
    first_year = max(train_start.year, WEATHER_FIRST_YEAR)
    last_year = min((end + pd.Timedelta(weeks=horizon)).year,
                    pd.Timestamp.today().year)
    parts = []
    try:
        if any(v in EXOG and v not in ("EUR", "USD") for v in exog):
            parts.append(load_weather_weekly_years(area, first_year, last_year))
        if any(v in ("EUR", "USD") for v in exog):
            parts.append(load_exchange_rates_weekly(first_year))
    except Exception as err:  # API down or rate limited
        st.error("Could not download the exogenous data (open-meteo or Norges "
                 "Bank). Try again in a minute, or forecast without exogenous "
                 f"variables.\n\nDetails: {err}")
        st.stop()
    X = pd.concat(parts, axis=1)

# ---------- Forecast ----------
settings = dict(history_weeks=history_weeks, horizon=horizon, p=int(p), d=int(d),
                q=int(q), m=int(m), sp=int(sp), sd=int(sd), sq=int(sq),
                learning_rate=lr, future=future)
try:
    forecast = cached_forecast(y, X, tuple(exog), end, tuple(settings.items()))
except Exception as err:
    st.error("The forecast could not be computed with these settings (e.g. "
             "too short history for the chosen season length).\n\n"
             f"Details: {err}")
    st.stop()

actual = y.reindex(forecast.index)
baseline = seasonal_naive(y, end, horizon)
history = y[(y.index > end - pd.Timedelta(weeks=52)) & (y.index <= end)]

# ---------- Key numbers ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Filling, week {end.isocalendar().week} {end.year}",
          f"{y.loc[end]:.1f} %")
k2.metric(f"Forecast in {horizon} weeks", f"{forecast.iloc[-1]:.1f} %",
          f"{forecast.iloc[-1] - y.loc[end]:+.1f} pp")
if actual.notna().any():
    k3.metric("Mean error (MAE)", f"{(forecast - actual).abs().mean():.1f} pp",
              help="Mean absolute error against the actual filling, for the "
                   "weeks that are known.")
    k4.metric("Baseline MAE", f"{(baseline - actual).abs().mean():.1f} pp",
              help="Newest level plus last year's change over the same weeks. "
                   "The model should beat this.")
else:
    k3.metric("Mean error (MAE)", "–", help="The forecast lies in the future.")
    k4.metric("Baseline in " f"{horizon} weeks", f"{baseline.iloc[-1]:.1f} %")

# The conclusion in one sentence
last_week = forecast.index[-1]
area_rows = fill[fill["area_number"] == number]
normal = weekly_normal(area_rows, last_week.year)["median"].get(
    last_week.isocalendar().week)
text = (f"The model expects **{area}** to "
        f"{'fall' if forecast.iloc[-1] < y.loc[end] else 'rise'} from "
        f"**{y.loc[end]:.1f} %** to **{forecast.iloc[-1]:.1f} %** by week "
        f"{last_week.isocalendar().week}, {last_week.year}")
if normal is not None and pd.notna(normal):
    text += f" (normal for that week: {normal:.1f} %)"
if pd.notna(actual.iloc[-1]):
    text += f". The real value was **{actual.iloc[-1]:.1f} %**"
st.info(text + ".", icon="💡")

# ---------- Animated plot: the forecast is drawn one week at a time ----------
# The forecast line starts at the last known week, so it joins the history
fc_x = [end] + list(forecast.index)
fc_y = [y.loc[end]] + list(forecast.values)

fig = go.Figure()
fig.add_scatter(x=history.index, y=history, mode="lines", name="History",
                line=dict(color=COLORS["dark"], width=2))
if actual.notna().any():
    fig.add_scatter(x=actual.index, y=actual, mode="lines", name="Actual",
                    line=dict(color=COLORS["dark"], dash="dash"))
fig.add_scatter(x=baseline.index, y=baseline, mode="lines", name="Baseline",
                line=dict(color=COLORS["neutral"], dash="dot"))
forecast_trace = len(fig.data)
fig.add_scatter(x=fc_x[:2], y=fc_y[:2], mode="lines+markers", name="Forecast",
                line=dict(color=COLORS["accent"], width=3), marker=dict(size=6))

# One frame per forecast week; only the forecast trace changes
fig.frames = [
    go.Frame(data=[go.Scatter(x=fc_x[:k + 1], y=fc_y[:k + 1])],
             traces=[forecast_trace], name=str(k))
    for k in range(1, len(fc_x))
]
play = dict(label="▶ Play", method="animate",
            args=[None, dict(frame=dict(duration=250, redraw=False),
                             transition=dict(duration=0), fromcurrent=True)])
pause = dict(label="❚❚ Pause", method="animate",
             args=[[None], dict(frame=dict(duration=0, redraw=False),
                                mode="immediate")])
fig.update_layout(
    height=480, yaxis=dict(title="Filling degree (%)", range=[0, 100]),
    xaxis=dict(range=[history.index[0], forecast.index[-1]
                      + pd.Timedelta(weeks=1)]),
    updatemenus=[dict(type="buttons", buttons=[play, pause], x=0, y=-0.12,
                      xanchor="left", yanchor="top", direction="right")],
    sliders=[dict(
        active=len(fig.frames) - 1, x=0.18, len=0.82, y=-0.08,
        currentvalue=dict(prefix="Forecast week: "),
        steps=[dict(label=str(k), method="animate",
                    args=[[str(k)], dict(frame=dict(duration=0, redraw=False),
                                         mode="immediate")])
               for k in range(1, len(fc_x))])],
    margin=dict(b=90),
)
# Start by showing the whole forecast; Play draws it again week by week
fig.data[forecast_trace].update(x=fc_x, y=fc_y)
st.plotly_chart(fig, theme=None)

with st.expander("Forecast table"):
    st.dataframe(pd.DataFrame({"Forecast (%)": forecast, "Actual (%)": actual,
                               "Baseline (%)": baseline}).round(1)
                 .rename_axis("Week (Sunday)"))
    csv_download(pd.DataFrame({"forecast": forecast, "actual": actual,
                               "baseline": baseline}).rename_axis("week"),
                 f"forecast_{area}_{end:%Y-%m-%d}.csv")

with st.expander("About the model"):
    st.markdown(
        "- **SNARIMAX** (River) learns one week at a time and forecasts "
        "recursively, so every forecast week builds on the previous ones "
        "(dynamic forecasting).\n"
        "- **Weekly resolution**, the resolution of Magasinstatistikk; "
        "weather and exchange rates are put on the same Sunday weeks.\n"
        "- **Exogenous variables**: their future values are unknown, so the "
        "averages for the same weeks in the training period are used unless "
        "'Observed' is chosen for a forecast in the past.\n"
        "- **Area and week** follow the sidebar and the map."
    )
