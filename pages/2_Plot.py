"""Side 3: Interaktivt plott med valg av kolonne og måneder."""
import io
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import streamlit as st

from utils import MEASURE_COLS, UNITS, load_data  # felles innlesing med caching

st.set_page_config(page_title="Plot", page_icon="📈", layout="wide")
st.title("📈 Reservoir Plot")

df = load_data()

# Nedtrekksmeny: én kolonne, eller alle kolonnene samtidig
ALL = "All columns"
choice = st.selectbox("Select column", [ALL] + MEASURE_COLS)

# Glidebryter for å velge et utvalg av måneder. Standard er første måned.
months = df["month"].unique().tolist()
start_month, end_month = st.select_slider(
    "Select months", options=months, value=(months[0], months[0])
)

# Månedene har formatet "ÅÅÅÅ-MM", så vanlig tekstsammenligning gir riktig rekkefølge
subset = df[(df["month"] >= start_month) & (df["month"] <= end_month)]

# Punktmarkører bare når det er få punkter; ellers blir kurven rotete
marker = "o" if len(subset) <= 60 else None

# layout="constrained" gir fast plass til akser og etiketter,
# slik at bildet beholder samme størrelse når perioden endres
fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")

if choice == ALL:
    # Kolonnene har ulike skalaer (TWh vs. andel 0-1). Hver kolonne normaliseres
    # til 0-1 med min/maks fra HELE datasettet, slik at kurvene ikke hopper
    # når man endrer perioden.
    lo = df[MEASURE_COLS].min()
    spread = (df[MEASURE_COLS].max() - lo).replace(0, 1)  # unngå deling på 0
    for col in MEASURE_COLS:
        ax.plot(subset["date"], (subset[col] - lo[col]) / spread[col],
                marker=marker, markersize=4, label=col)
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("Normalised value (0-1)")
    # Forklaringen plasseres under plottet, så den aldri dekker kurvene
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=9)
else:
    ax.plot(subset["date"], subset[choice], marker=marker, markersize=4, color="tab:blue")
    # Fast y-akse basert på hele datasettet gjør det lett å sammenligne perioder
    lo, hi = df[choice].min(), df[choice].max()
    pad = (hi - lo) * 0.05 or 0.01
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_ylabel(UNITS[choice])

# Datoakse som tilpasser seg lengden på perioden (uker, måneder eller år)
locator = mdates.AutoDateLocator()
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

ax.set_title(f"{choice} – {start_month} to {end_month} (Norway, weekly)")
ax.set_xlabel("Date")
ax.grid(True, linestyle="--", alpha=0.5)

# Lagre figuren selv (uten automatisk beskjæring) og vis den som bilde,
# slik at plottet beholder samme størrelse når perioden endres
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150)
st.image(buf)

st.caption("Source: data/reservoirs.csv (national total, area type 'NO').")
