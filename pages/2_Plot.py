"""Side 3: Interaktivt plott med valg av områdetype, kolonne og periode."""
import io

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import streamlit as st

from utils import AREA_TYPES, MEASURE_COLS, UNITS, area_label, load_data

st.title("📈 Reservoir Plot")

# Radioknapper: områdetype. Plottet får én linje per områdenummer i typen.
area_type = st.radio(
    "Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, horizontal=True
)
choice = st.selectbox("Select column", MEASURE_COLS, format_func=lambda c: f"{c} – {UNITS[c]}")

# Alle tilgjengelige måneder for valgt områdetype
all_data = load_data(area_type)
months = sorted(all_data["month"].unique().tolist())

# Glidebryteren styrer nå hvilket tidsintervall som lastes inn (standard: siste år)
default_start = months[-12] if len(months) >= 12 else months[0]
start_month, end_month = st.select_slider(
    "Select period to load", options=months, value=(default_start, months[-1])
)
subset = load_data(area_type, start_month, end_month)

# Punktmarkører bare når det er få punkter per linje; ellers blir kurven rotete
points_per_line = len(subset) / max(subset["area_number"].nunique(), 1)
marker = "o" if points_per_line <= 60 else None

# layout="constrained" gir fast plass til akser og etiketter
fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")

# Én linje per områdenummer (f.eks. NO1-NO5 for EL)
for number, area_df in subset.groupby("area_number"):
    ax.plot(area_df["date"], area_df[choice], marker=marker, markersize=3,
            label=area_label(area_type, number))

# Fast y-akse basert på alle data for områdetypen gjør det lett å sammenligne perioder
lo, hi = all_data[choice].min(), all_data[choice].max()
pad = (hi - lo) * 0.05 or 0.5
ax.set_ylim(lo - pad, hi + pad)
ax.set_ylabel(UNITS[choice])

# Datoakse som tilpasser seg lengden på perioden (uker, måneder eller år)
locator = mdates.AutoDateLocator()
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

ax.set_title(f"{choice} – {start_month} to {end_month} ({AREA_TYPES[area_type]}, weekly)")
ax.set_xlabel("Date")
ax.grid(True, linestyle="--", alpha=0.5)
# Forklaringen plasseres under plottet, så den aldri dekker kurvene
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5, fontsize=9)

# Lagre figuren selv (uten automatisk beskjæring) og vis den som bilde,
# slik at plottet beholder samme størrelse når perioden endres
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150)
st.image(buf)
plt.close(fig)  # frigjør minne; Streamlit kjører skriptet på nytt ved hver endring

st.caption(
    "Source: NVE Magasinstatistikk API. The slider selects which period is loaded "
    "and plotted; the API response itself is cached for one hour."
)
