"""Electricity flows between Norway and neighbouring countries (MongoDB).

The connection defaults to one from the price area chosen in the global
selector in the sidebar (e.g. NO3 -> NO_3-SE_2).
"""
import calendar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import COLORS, DIRECTION_COLORS  # shared palette and Plotly template
from utils import MONGO, load_flows, load_or_stop

st.title("🔌 Cross-border Flows")
st.write(
    "Electricity flowing out of Norway (export) and into Norway (import) "
    "through each cross-border connection, 2024–2025."
)

# Daily flows from MongoDB; if the database cannot be reached (or the
# connection is not configured), a readable message is shown instead
flows = load_or_stop(MONGO, load_flows, hint="Check the internet connection "
                     "and the MongoDB settings, or try again later.")
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
    fig = go.Figure(go.Pie(
        labels=[d.capitalize() for d in totals.index], values=totals.values,
        hole=0.42, sort=False, direction="clockwise", rotation=0,
        marker=dict(colors=[DIRECTION_COLORS.get(d, COLORS["neutral"])
                            for d in totals.index],
                    line=dict(color="white", width=3)),
        texttemplate="<b>%{percent:.0%}</b>",
        textfont=dict(color="white", size=14),
        hovertemplate="%{label}: %{value:.2f} TWh<extra></extra>",
    ))
    fig.update_layout(
        title=f"{connection}, {year}", height=420, hovermode="closest",
        annotations=[dict(text=f"<b>{totals.sum():.2f}</b><br>TWh total",
                          showarrow=False, font=dict(size=16))],
        legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center",
                    yanchor="top"),
    )
    st.plotly_chart(fig, theme=None)

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
        fig = go.Figure()
        # One line per direction. Days in months that are not selected are
        # set to NaN, so the line breaks instead of crossing the gap.
        all_days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
        for direction, dir_df in year_df.groupby("direction"):
            series = (dir_df.set_index("date")["energy_mwh"]
                      .reindex(all_days) / 1000)  # GWh
            series[~series.index.month.isin(months)] = float("nan")
            # Import is dashed, so the two blue lines are easy to tell apart
            fig.add_scatter(
                x=series.index, y=series, mode="lines",
                name=direction.capitalize(), connectgaps=False,
                line=dict(width=1.6,
                          dash="dash" if direction == "import" else "solid",
                          color=DIRECTION_COLORS.get(direction,
                                                     COLORS["neutral"])),
                hovertemplate="%{y:.1f} GWh",
            )

        # Only show the range around the selected months
        fig.update_layout(
            title=f"{connection}, {year}", height=420,
            yaxis_title="Energy per day (GWh)",
            xaxis_range=[pd.Timestamp(year, min(months), 1),
                         pd.Timestamp(year, max(months), 1)
                         + pd.offsets.MonthEnd(0)],
        )
        st.plotly_chart(fig, theme=None)

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
