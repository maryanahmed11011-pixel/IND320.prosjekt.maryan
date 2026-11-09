"""Electricity flows between Norway and neighbouring countries (MongoDB).

The connection defaults to one from the price area chosen in the global
selector in the sidebar (e.g. NO3 -> NO_3-SE_2).
"""
import calendar

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from theme import COLORS, DIRECTION_COLORS  # shared palette and plot style
from utils import load_flows

st.title("🔌 Cross-border Flows")
st.write(
    "Electricity flowing out of Norway (export) and into Norway (import) "
    "through each cross-border connection, 2024–2025."
)

flows = load_flows()
connections = sorted(flows["connection"].unique())

# Default connection: the first one from the price area in the sidebar
area = st.session_state.get("price_area", "NO3")
prefix = f"NO_{area[-1]}-" if area.startswith("NO") else None
matches = [c for c in connections if prefix and c.startswith(prefix)]
default_idx = connections.index(matches[0]) if matches else 0

# Two columns: pie chart on the left, line plot on the right
left, right = st.columns(2)

# ---------- Left: pie chart for one year ----------
with left:
    st.subheader("Yearly total")
    connection = st.radio("Connection", connections, index=default_idx)
    year = int(st.selectbox("Year", sorted(flows["year"].unique(), reverse=True)))

    # Sum daily energy per direction for the connection and year (MWh -> TWh)
    year_df = flows[(flows["connection"] == connection) & (flows["year"] == year)]
    totals = year_df.groupby("direction")["energy_mwh"].sum() / 1e6

    # Donut chart in the shared palette: export blue, import dark blue,
    # white gaps between the slices and the total in the middle
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        totals,
        labels=[f"{d.capitalize()}\n{v:.2f} TWh" for d, v in totals.items()],
        colors=[DIRECTION_COLORS.get(d, COLORS["neutral"]) for d in totals.index],
        autopct="%1.0f%%", pctdistance=0.78, startangle=90, counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 3},
        textprops={"color": COLORS["dark"], "fontsize": 11},
    )
    # Percentages inside the ring in white, so they read on the colours
    for text in ax.texts:
        if text.get_text().endswith("%"):
            text.set_color("white")
            text.set_fontweight("bold")
    ax.text(0, 0, f"{totals.sum():.2f}\nTWh total", ha="center", va="center",
            fontsize=13, fontweight="bold", color=COLORS["dark"])
    ax.set_title(f"{connection}, {year}")
    ax.set_aspect("equal")
    ax.axis("off")  # no grid or axes around the donut
    st.pyplot(fig)
    plt.close(fig)

# ---------- Right: line plot for selected months ----------
with right:
    st.subheader("Daily flow in selected months")
    # Pills: choose which months to include (several can be selected)
    months = st.pills(
        "Months", options=list(range(1, 13)),
        format_func=lambda m: calendar.month_abbr[m],
        selection_mode="multi", default=[1],
    )

    if not months:
        st.info("Select at least one month.")
    else:
        fig, ax = plt.subplots(figsize=(7, 5))
        # One line per direction. Days in months that are not selected are
        # set to NaN, so the line breaks instead of crossing the gap.
        all_days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
        for direction, dir_df in year_df.groupby("direction"):
            series = (dir_df.set_index("date")["energy_mwh"]
                      .reindex(all_days) / 1000)  # GWh
            series[~series.index.month.isin(months)] = float("nan")
            # Import is dashed, so the two blue lines are easy to tell apart
            ax.plot(series.index, series, linewidth=1.4,
                    linestyle="--" if direction == "import" else "-",
                    color=DIRECTION_COLORS.get(direction, COLORS["neutral"]),
                    label=direction.capitalize())

        # Only show the range around the selected months
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

# ---------- Source ----------
with st.expander("About the data"):
    st.markdown(
        "- **Source:** ENTSO-E Transparency Platform, *Physical Flows* (cross-border), "
        "retrieved with the `entsoe-py` library for 2024–2025.\n"
        "- **Processing:** Hourly values were stored in a local Cassandra database with "
        "Spark, read back with Spark and aggregated to daily energy (MWh) per "
        "connection and direction.\n"
        "- **Storage:** The daily values are stored in MongoDB Atlas, which this page "
        "reads from.\n"
        "- **Directions:** *export* = out of Norway, *import* = into Norway. "
        "Times are in UTC.\n"
        "- **Default connection:** the first connection from the price area chosen "
        "in the sidebar."
    )
