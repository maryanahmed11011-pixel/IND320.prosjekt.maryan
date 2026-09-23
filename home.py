"""Side 1: Forside med nøkkeltall, sesongoversikt og snarveier til de andre sidene."""
import io

import matplotlib.pyplot as plt
import streamlit as st

from utils import load_data  # felles innlesing med caching

df = load_data()

# ---------- Toppseksjon ----------
st.title("💧 Norway's Water Battery")
st.markdown(
    "Around 90 % of Norway's electricity comes from hydropower. The water stored in the "
    "reservoirs works like a giant **battery**: it fills up with snowmelt in spring and summer, "
    "and is drained through the winter when electricity demand is high. "
    "This app explores weekly reservoir data from **1995 until today**."
)
st.caption("IND320 – Compulsory work 1 · Data: data/reservoirs.csv (national total)")

# ---------- Nøkkeltall for siste uke ----------
latest = df.iloc[-1]  # dataene er sortert etter dato, så siste rad er nyeste uke
year, week = int(latest["iso_year"]), int(latest["iso_week"])

# Samme uke i fjor, og historisk median for denne uka (alle tidligere år)
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
    "Stored energy",
    f"{latest['filling_TWh']:.1f} TWh",
    f"of {latest['capacity_TWh']:.1f} TWh capacity",
    delta_color="off",
)
if not last_year.empty:
    diff = (latest["filling_degree"] - last_year["filling_degree"].iloc[0]) * 100
    c3.metric("Compared to last year", f"{diff:+.1f} pp", "same week", delta_color="off")
if week in median_by_week.index:
    diff = (latest["filling_degree"] - median_by_week[week]) * 100
    c4.metric("Compared to normal", f"{diff:+.1f} pp", "vs. median since 1995", delta_color="off")

# ---------- Sesongplott: i år mot historien ----------
st.subheader("🌊 This year compared to history")

# Min, maks og median for hver ukenummer over alle tidligere år
band = history.groupby("iso_week")["filling_degree"].agg(["min", "median", "max"]) * 100
this_year = df[df["iso_year"] == year]
prev_year = df[df["iso_year"] == year - 1]

fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
ax.fill_between(band.index, band["min"], band["max"], color="#9ecae1", alpha=0.5,
                label=f"Range {int(history['iso_year'].min())}–{year - 1}")
ax.plot(band.index, band["median"], color="#3182bd", linestyle="--", label="Median")
ax.plot(prev_year["iso_week"], prev_year["filling_degree"] * 100, color="grey", label=str(year - 1))
ax.plot(this_year["iso_week"], this_year["filling_degree"] * 100, color="#08306b",
        linewidth=2.5, label=str(year))
ax.set_xlim(1, 53)
ax.set_ylim(0, 100)
ax.set_xlabel("Week number")
ax.set_ylabel("Filling degree (%)")
ax.grid(True, linestyle="--", alpha=0.4)
ax.legend(loc="lower right", fontsize=9)

# Fast bildestørrelse (samme metode som på plottsiden)
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150)
st.image(buf)
plt.close(fig)
st.caption("The reservoirs are lowest around week 15–18 (April) and highest around week 40 (October).")

# ---------- Rekorder ----------
st.subheader("🏆 Records since 1995")
hi = df.loc[df["filling_degree"].idxmax()]
lo = df.loc[df["filling_degree"].idxmin()]
r1, r2 = st.columns(2)
r1.success(f"**Highest:** {hi['filling_degree'] * 100:.1f} % in week {int(hi['iso_week'])}, {int(hi['iso_year'])}")
r2.error(f"**Lowest:** {lo['filling_degree'] * 100:.1f} % in week {int(lo['iso_week'])}, {int(lo['iso_year'])}")

# ---------- Snarveier til de andre sidene ----------
st.subheader("🧭 Explore the data")
p1, p2, p3 = st.columns(3)
with p1.container(border=True):
    st.markdown("**Data Table**  \nOne row per column, with mini charts of the first month.")
    st.page_link("pages/1_Data_Table.py", label="Open table", icon="📊")
with p2.container(border=True):
    st.markdown("**Plot**  \nChoose columns and months in an interactive plot.")
    st.page_link("pages/2_Plot.py", label="Open plot", icon="📈")
with p3.container(border=True):
    st.markdown("**Future Work**  \nWhat comes next: MongoDB and more.")
    st.page_link("pages/3_Future_Work.py", label="Open page", icon="⚙️")

# ---------- Lenker ----------
st.divider()
st.markdown(
    "🔗 [GitHub repository](https://github.com/maryanahmed11011-pixel/IND320.prosjekt.maryan) · "
    "[Streamlit app](https://ind320prosjektmaryan-lmvbjxajmrnrqkykq8ivne.streamlit.app/)"
)
