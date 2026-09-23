"""Side 3: Interaktivt plott med valg av kolonne og måneder."""
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

fig, ax = plt.subplots(figsize=(10, 5))

if choice == ALL:
    # Kolonnene har ulike skalaer (TWh vs. andel 0-1), så hver kolonne
    # min-max-normaliseres til 0-1 innenfor valgt periode før plotting.
    for col in MEASURE_COLS:
        values = subset[col]
        spread = values.max() - values.min()
        normalised = (values - values.min()) / spread if spread != 0 else values * 0
        ax.plot(subset["date"], normalised, marker="o", label=col)
    ax.set_ylabel("Normalised value (0-1)")
    ax.legend(loc="best")
else:
    ax.plot(subset["date"], subset[choice], marker="o", color="tab:blue")
    ax.set_ylabel(UNITS[choice])

ax.set_title(f"{choice} – {start_month} to {end_month} (Norway, weekly)")
ax.set_xlabel("Date")
ax.grid(True, linestyle="--", alpha=0.5)
fig.autofmt_xdate()  # skråstilte datoer så de ikke overlapper

st.pyplot(fig)
st.caption("Source: data/reservoirs.csv (national total, area type 'NO').")
