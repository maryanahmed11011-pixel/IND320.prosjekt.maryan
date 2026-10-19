"""Side 4: Strømflyt mellom Norge og nabolandene (data fra MongoDB)."""
import calendar

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from utils import load_flows

st.title("🔌 Cross-border Flows")
st.write(
    "Electricity flowing out of Norway (export) and into Norway (import) "
    "through each cross-border connection, 2024–2025."
)

flows = load_flows()

# To kolonner: kakediagram til venstre, linjeplott til høyre
left, right = st.columns(2)

# ---------- Venstre side: kakediagram for ett år ----------
with left:
    st.subheader("Yearly total")
    connection = st.radio("Connection", sorted(flows["connection"].unique()))
    year = int(st.selectbox("Year", sorted(flows["year"].unique(), reverse=True)))

    # Summer daglig energi per retning for valgt forbindelse og år (MWh -> TWh)
    year_df = flows[(flows["connection"] == connection) & (flows["year"] == year)]
    totals = year_df.groupby("direction")["energy_mwh"].sum() / 1e6

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(totals, labels=[f"{d} ({v:.2f} TWh)" for d, v in totals.items()],
           autopct="%1.0f%%", startangle=90)
    ax.set_title(f"{connection}, {year}")
    st.pyplot(fig)
    plt.close(fig)

# ---------- Høyre side: linjeplott for valgte måneder ----------
with right:
    st.subheader("Daily flow in selected months")
    # Pills: velg hvilke måneder som skal være med (flere kan velges)
    months = st.pills(
        "Months", options=list(range(1, 13)), format_func=lambda m: calendar.month_abbr[m],
        selection_mode="multi", default=[1],
    )

    if not months:
        st.info("Select at least one month.")
    else:
        fig, ax = plt.subplots(figsize=(7, 5))
        # Én linje per retning. Dagene i måneder som ikke er valgt settes til NaN,
        # slik at linjen får et brudd i stedet for å trekkes over ikke-valgte måneder.
        all_days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
        for direction, dir_df in year_df.groupby("direction"):
            series = dir_df.set_index("date")["energy_mwh"].reindex(all_days) / 1000  # GWh
            series[~series.index.month.isin(months)] = float("nan")
            ax.plot(series.index, series, linewidth=1, label=f"{connection} {direction}")

        # Vis bare området rundt de valgte månedene
        ax.set_xlim(pd.Timestamp(year, min(months), 1),
                    pd.Timestamp(year, max(months), 1) + pd.offsets.MonthEnd(0))
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.set_ylabel("Energy per day (GWh)")
        ax.set_title(f"{connection}, {year}")
        ax.grid(True, alpha=0.4)
        ax.legend()
        st.pyplot(fig)
        plt.close(fig)

# ---------- Kilde ----------
with st.expander("About the data"):
    st.markdown(
        "- **Source:** ENTSO-E Transparency Platform, *Physical Flows* (cross-border), "
        "retrieved with the `entsoe-py` library for 2024–2025.\n"
        "- **Processing:** Hourly values were stored in a local Cassandra database with "
        "Spark, read back with Spark and aggregated to daily energy (MWh) per "
        "connection and direction.\n"
        "- **Storage:** The daily values are stored in MongoDB Atlas, which this page reads from.\n"
        "- **Directions:** *export* = out of Norway, *import* = into Norway. "
        "Times are in UTC."
    )
