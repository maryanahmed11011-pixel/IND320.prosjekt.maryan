"""Front page: key figures, seasonal overview and shortcuts to all pages."""
import io

import matplotlib.pyplot as plt
import streamlit as st

from theme import COLORS  # shared palette (also applies the plot style)
from utils import load_data  # shared, cached data loading

df = load_data("NO")  # national total from the NVE API

# ---------- Top section ----------
st.title("💧 Norway's Water Battery")
st.markdown(
    "Around 90 % of Norway's electricity comes from hydropower. The water stored in the "
    "reservoirs works like a giant **battery**: it fills up with snowmelt in spring and summer, "
    "and is drained through the winter when electricity demand is high. "
    "This app explores weekly reservoir data from **1995 until today**, together with "
    "**hourly weather data** (ERA5) that explains how the reservoirs are filled."
)
st.caption("IND320 – Compulsory work 3 · Data: NVE Magasinstatistikk API, "
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

fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
ax.fill_between(band.index, band["min"], band["max"], color=COLORS["light"],
                alpha=0.5,
                label=f"Range {int(history['iso_year'].min())}–{year - 1}")
ax.plot(band.index, band["median"], color=COLORS["primary"], linestyle="--",
        label="Median")
ax.plot(prev_year["iso_week"], prev_year["filling_degree"] * 100,
        color=COLORS["neutral"], label=str(year - 1))
ax.plot(this_year["iso_week"], this_year["filling_degree"] * 100,
        color=COLORS["dark"], linewidth=2.5, label=str(year))
ax.set_xlim(1, 53)
ax.set_ylim(0, 100)
ax.set_xlabel("Week number")
ax.set_ylabel("Filling degree (%)")
ax.legend(loc="lower right", fontsize=9)

# Fixed image size (same method as on the plot page)
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150)
st.image(buf)
plt.close(fig)
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
st.caption("Choose an area in the sidebar: it is used as the default on all pages.")

CARDS = [
    ("Data Table", "One row per area, with mini charts of the first month.",
     "pages/1_Data_Table.py", "Open", "📊"),
    ("Plot", "Compare areas over a chosen period in an interactive plot.",
     "pages/2_Plot.py", "Open", "📈"),
    ("Reservoir Analysis", "Seasonal-trend decomposition (STL) and spectrogram "
     "of the filling degree.", "pages/5_Reservoir_Analysis.py",
     "Open", "🔍"),
    ("Weather Anomalies", "Heavy rain and abrupt temperature changes found with "
     "SPC and LOF on ERA5 data.", "pages/6_Weather_Anomalies.py",
     "Open", "🌦️"),
    ("Cross-border Flows", "Electricity in and out of Norway, from MongoDB.",
     "pages/4_Cross_Border.py", "Open", "🔌"),
]
cols = st.columns(len(CARDS))
for col, (title, text, page, label, icon) in zip(cols, CARDS):
    with col.container(border=True):
        st.markdown(f"**{title}**  \n{text}")
        st.page_link(page, label=label, icon=icon)

# ---------- Links ----------
st.divider()
st.markdown(
    "🔗 [GitHub repository](https://github.com/maryanahmed11011-pixel/IND320.prosjekt.maryan) · "
    "[Streamlit app](https://ind320prosjektmaryan-lmvbjxajmrnrqkykq8ivne.streamlit.app/)"
)
