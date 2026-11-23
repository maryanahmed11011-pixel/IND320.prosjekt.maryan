"""Front page: key figures, seasonal overview and shortcuts to all pages."""
import plotly.graph_objects as go
import streamlit as st

from theme import COLORS  # shared palette (also registers the Plotly template)
from utils import load_data  # shared, cached data loading

df = load_data("NO")  # national total from the NVE API

# ---------- Top section ----------
st.title(" Norway's Water Battery")
st.markdown(
    "Around 90 % of Norway's electricity comes from hydropower. The water stored in the "
    "reservoirs works like a giant **battery**: it fills up with snowmelt in spring and summer, "
    "and is drained through the winter when electricity demand is high. "
    "This app explores weekly reservoir data from **1995 until today**, together with "
    "**hourly weather data** (ERA5) that explains how the reservoirs are filled."
)
st.caption("IND320 – Compulsory work 4 · Data: NVE Magasinstatistikk API, "
           "open-meteo (ERA5) and ENTSO-E (via MongoDB)")

# ---------- Key figures for the latest week ----------
latest = df.iloc[-1]  # data is sorted by date, so the last row is the newest week
year, week = int(latest["iso_year"]), int(latest["iso_week"])

# Same week last year, and historical median for this week (all earlier years)
last_year = df[(df["iso_year"] == year - 1) & (df["iso_week"] == week)]
history = df[df["iso_year"] < year]
median_by_week = history.groupby("iso_week")["filling_degree"].median()

st.subheader(f"📍 Status week {week}, {year}")
c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Filling degree",
    f"{latest['filling_degree'] * 100:.1f} %",
    f"{latest['filling_degree_change'] * 100:+.1f} pp since last week",
)
c2.metric(
    f"Stored energy (capacity {latest['capacity_TWh']:.1f} TWh)",
    f"{latest['filling_TWh']:.1f} TWh",
)
if not last_year.empty:
    diff = (latest["filling_degree"] - last_year["filling_degree"].iloc[0]) * 100
    c3.metric("vs. same week last year", f"{diff:+.1f} pp",
              help="pp = percentage points")
if week in median_by_week.index:
    diff = (latest["filling_degree"] - median_by_week[week]) * 100
    c4.metric("vs. normal (median since 1995)", f"{diff:+.1f} pp",
              help="pp = percentage points")

# ---------- Seasonal plot: this year vs. history ----------
st.subheader("🌊 This year compared to history")

# Min, max and median for each week number over all earlier years
band = history.groupby("iso_week")["filling_degree"].agg(["min", "median", "max"]) * 100
this_year = df[df["iso_year"] == year]
prev_year = df[df["iso_year"] == year - 1]

fig = go.Figure()
# Historical range as a filled band: the max line is filled down to the
# min line ("tonexty"), so the band shows min-max for each week
fig.add_scatter(x=band.index, y=band["min"], mode="lines",
                line=dict(width=0), showlegend=False, hoverinfo="skip")
fig.add_scatter(x=band.index, y=band["max"], mode="lines",
                line=dict(width=0), fill="tonexty",
                fillcolor="rgba(158, 202, 225, 0.5)",  # COLORS["light"]
                name=f"Range {int(history['iso_year'].min())}–{year - 1}",
                hoverinfo="skip")
fig.add_scatter(x=band.index, y=band["median"], mode="lines", name="Median",
                line=dict(color=COLORS["primary"], dash="dash"),
                hovertemplate="%{y:.1f} %")
fig.add_scatter(x=prev_year["iso_week"], y=prev_year["filling_degree"] * 100,
                mode="lines", name=str(year - 1),
                line=dict(color=COLORS["neutral"]),
                hovertemplate="%{y:.1f} %")
fig.add_scatter(x=this_year["iso_week"], y=this_year["filling_degree"] * 100,
                mode="lines+markers", name=str(year),
                line=dict(color=COLORS["dark"], width=3),
                marker=dict(size=5), hovertemplate="%{y:.1f} %")
fig.update_layout(xaxis=dict(title="Week number", range=[1, 53]),
                  yaxis=dict(title="Filling degree (%)", range=[0, 100]),
                  height=400, hovermode="x unified")
st.plotly_chart(fig, theme=None)
st.caption("The reservoirs are lowest around week 15–18 (April) and highest "
           "around week 40 (October).")

# ---------- Records ----------
st.subheader("🏆 Records since 1995")
hi = df.loc[df["filling_degree"].idxmax()]
lo = df.loc[df["filling_degree"].idxmin()]
r1, r2 = st.columns(2)
r1.success(f"**Highest:** {hi['filling_degree'] * 100:.1f} % in week "
           f"{int(hi['iso_week'])}, {int(hi['iso_year'])}")
r2.error(f"**Lowest:** {lo['filling_degree'] * 100:.1f} % in week "
         f"{int(lo['iso_week'])}, {int(lo['iso_year'])}")

# ---------- Shortcuts to all pages, grouped like the menu ----------
st.subheader("🧭 Explore the data")
st.caption("Choose an area in the sidebar or on the map: it is used as the "
           "default on all pages.")

# Same groups and order as the menu (Overview, Explore, Analyse, Predict)
CARDS = [
    ("Map", "Areas coloured by reservoir filling or weather; click to "
     "select an area.", "pages/7_Map.py", "🗺️"),
    ("Reservoir Data", "Overview table with mini charts and an interactive "
     "plot.", "pages/1_Reservoir_Data.py", "📊"),
    ("Cross-border Flows", "Electricity in and out of Norway, from MongoDB.",
     "pages/4_Cross_Border.py", "🔌"),
    ("Exchange Rates", "EUR and USD against NOK from Norges Bank.",
     "pages/3_Exchange_Rates.py", "💱"),
    ("Reservoir Analysis", "Seasonal-trend decomposition (STL) and spectrogram "
     "of the filling degree.", "pages/5_Reservoir_Analysis.py", "🔍"),
    ("Weather Anomalies", "Unusual temperature and heavy rain found with SPC "
     "and LOF on ERA5 data.", "pages/6_Weather_Anomalies.py", "🌦️"),
    ("Weather vs. Reservoirs", "Sliding window correlation between weather "
     "and reservoir filling.", "pages/8_Correlation.py", "🔗"),
    ("Reservoir Forecast", "Forecast of the filling degree with River "
     "SNARIMAX.", "pages/9_Forecast.py", "🔮"),
]
# Two rows of four cards
for row in (CARDS[:4], CARDS[4:]):
    for col, (title, text, page, icon) in zip(st.columns(4), row):
        with col.container(border=True):
            st.markdown(f"**{title}**  \n{text}")
            st.page_link(page, label="Open", icon=icon)

# ---------- Links ----------
st.divider()
st.markdown(
    "🔗 [GitHub repository](https://github.com/maryanahmed11011-pixel/IND320.prosjekt.maryan) · "
    "[Streamlit app](https://ind320prosjektmaryan-lmvbjxajmrnrqkykq8ivne.streamlit.app/)"
)
