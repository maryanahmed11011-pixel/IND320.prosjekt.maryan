"""Front page: key figures, seasonal overview and shortcuts to all pages."""
import streamlit as st

import theme  # noqa: F401  shared palette, registers the Plotly template
from insights import reservoir_status, seasonal_figure, status_sentence
from utils import NVE, load_data, load_or_stop  # shared, cached data loading

# National total from the NVE API (a readable error message if it is down)
df = load_or_stop(NVE, load_data, "NO")

# ---------- Top section ----------
st.title("Hydropower Reservoirs in Norway")
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
status = reservoir_status(df)
year, week = status["year"], status["week"]
latest = df.iloc[-1]  # data is sorted by date, so the last row is the newest week

# The conclusion in one plain sentence, so the numbers do not need reading
st.info(status_sentence("Norway", status), icon="💡")

st.subheader(f"📍 Status week {week}, {year}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Filling degree", f"{status['value']:.1f} %",
          f"{status['week_change']:+.1f} pp since last week",
          help="pp = percentage points")
c2.metric(f"Stored energy (capacity {latest['capacity_TWh']:.1f} TWh)",
          f"{latest['filling_TWh']:.1f} TWh")
if status["vs_last_year"] is not None:
    c3.metric("Same week last year",
              f"{status['value'] - status['vs_last_year']:.1f} %",
              f"{status['vs_last_year']:+.1f} pp now",
              help="The arrow shows how much higher or lower the filling is "
                   "now than in the same week last year.")
if status["vs_normal"] is not None:
    c4.metric(f"Normal for week {week}", f"{status['normal']:.1f} %",
              f"{status['vs_normal']:+.1f} pp now",
              help=f"Median for the same week in {status['normal_period']}.")

# ---------- The five price areas side by side ----------
st.markdown("**Price areas compared with normal for this week**")
el = load_or_stop(NVE, load_data, "EL")
for col, (number, area_df) in zip(st.columns(5), el.groupby("area_number")):
    s = reservoir_status(area_df)
    if s:
        col.metric(f"NO{number}", f"{s['value']:.1f} %",
                   None if s["vs_normal"] is None
                   else f"{s['vs_normal']:+.1f} pp vs normal",
                   help=f"Normal = median for week {s['week']} in "
                        f"{s['normal_period']}.")

# ---------- Seasonal plot: this year vs. history ----------
st.subheader("🌊 This year compared to history")
st.plotly_chart(seasonal_figure(df, "Norway"), theme=None)
st.caption("The reservoirs are lowest around week 15–18 (April) and highest "
           "around week 40 (October). The band shows the lowest and highest "
           "filling for each week in earlier years.")

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
