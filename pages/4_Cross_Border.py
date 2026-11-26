"""Electricity flows between Norway and neighbouring countries (MongoDB).

The connection defaults to one from the price area chosen in the global
selector in the sidebar (e.g. NO3 -> NO_3-SE_2).
"""
import calendar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import COLORS, DIRECTION_COLORS  # shared palette and Plotly template
from insights import csv_download
from utils import MONGO, load_flows, load_geojson, load_or_stop

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

# Readable names for the ENTSO-E bidding zone codes (the data keeps the codes)
ZONES = {
    "SE_1": "Sweden (SE1)", "SE_2": "Sweden (SE2)", "SE_3": "Sweden (SE3)",
    "SE_4": "Sweden (SE4)", "FI": "Finland", "DK_1": "Denmark (DK1)",
    "DE_LU": "Germany", "NL": "Netherlands", "GB": "Great Britain",
    "RU": "Russia",
}


def connection_label(code):
    """'NO_2-DE_LU' -> 'NO2 ↔ Germany'."""
    norway, other = code.split("-", 1)
    return f"{norway.replace('_', '')} ↔ {ZONES.get(other, other)}"


# Rough position (lat, lon) of each neighbouring zone, where its line ends
ZONE_POS = {
    "SE_1": (67.6, 20.6), "SE_2": (64.0, 16.5), "SE_3": (59.6, 14.2),
    "SE_4": (56.2, 14.0), "FI": (68.6, 27.4), "DK_1": (56.3, 9.2),
    "DE_LU": (53.9, 9.6), "NL": (53.4, 6.8), "GB": (55.1, -1.6),
    "RU": (69.2, 31.0),
}

# ---------- Year (used by the whole page) ----------
year = int(st.selectbox("Year", sorted(flows["year"].unique(), reverse=True),
                        key="flow_year"))
year_all = flows[flows["year"] == year]
per_conn = (year_all.groupby(["connection", "direction"])["energy_mwh"].sum()
            .unstack(fill_value=0) / 1e6)  # TWh
for direction in ("export", "import"):
    if direction not in per_conn:
        per_conn[direction] = 0.0
per_conn["net"] = per_conn["export"] - per_conn["import"]

# The conclusion in one sentence
total_exp, total_imp = per_conn["export"].sum(), per_conn["import"].sum()
biggest = per_conn["export"].idxmax()
st.info(
    f"In **{year}** Norway exported **{total_exp:.1f} TWh** and imported "
    f"**{total_imp:.1f} TWh** through these connections – a net "
    f"{'export' if total_exp >= total_imp else 'import'} of "
    f"**{abs(total_exp - total_imp):.1f} TWh**. Most was exported through "
    f"**{connection_label(biggest)}** ({per_conn.loc[biggest, 'export']:.1f} TWh).",
    icon="💡")

# ---------- Flow map: one line per connection, thickness = net flow ----------
st.subheader("Where does the electricity go?")
no_pos = {f["properties"]["region"]: (f["properties"]["lat"], f["properties"]["lon"])
          for f in load_or_stop("the GeoJSON files in geo/", load_geojson,
                                "price")["features"]}
biggest_net = per_conn["net"].abs().max() or 1
flow_fig = go.Figure()
for code, row in per_conn.iterrows():
    norway, other = code.split("-", 1)
    start, stop = no_pos.get(norway.replace("_", "")), ZONE_POS.get(other)
    if start is None or stop is None:
        continue
    exporting = row["net"] >= 0
    # The line is drawn in the direction of the net flow, so the arrow at
    # its end points to where the electricity goes
    a, b = (start, stop) if exporting else (stop, start)
    hover = (f"<b>{connection_label(code)}</b><br>Export: {row['export']:.2f} TWh"
             f"<br>Import: {row['import']:.2f} TWh<br>Net: {row['net']:+.2f} TWh"
             "<extra></extra>")
    flow_fig.add_scattergeo(
        lat=[a[0], b[0]], lon=[a[1], b[1]], mode="lines+markers",
        line=dict(width=1.5 + 9 * abs(row["net"]) / biggest_net,
                  color=COLORS["primary"] if exporting else COLORS["accent"]),
        marker=dict(symbol="arrow", size=[0, 16], angleref="previous",
                    color=COLORS["primary"] if exporting else COLORS["accent"]),
        hovertemplate=hover, showlegend=False,
    )
    # Net value in the middle of the line
    flow_fig.add_scattergeo(
        lat=[(a[0] + b[0]) / 2], lon=[(a[1] + b[1]) / 2], mode="text",
        text=[f"{abs(row['net']):.1f}"], textfont=dict(size=12, color=COLORS["dark"]),
        hovertemplate=hover, showlegend=False)
# Names of the Norwegian areas and of the neighbours
flow_fig.add_scattergeo(
    lat=[p[0] for p in no_pos.values()], lon=[p[1] for p in no_pos.values()],
    mode="markers+text", text=list(no_pos), textposition="top center",
    marker=dict(size=7, color=COLORS["dark"]), hoverinfo="skip", showlegend=False)
used = sorted({c.split("-", 1)[1] for c in per_conn.index} & set(ZONE_POS))
flow_fig.add_scattergeo(
    lat=[ZONE_POS[z][0] for z in used], lon=[ZONE_POS[z][1] for z in used],
    mode="text", text=[ZONES.get(z, z) for z in used], textposition="bottom center",
    textfont=dict(size=11, color=COLORS["neutral"]), hoverinfo="skip",
    showlegend=False)
# Legend entries for the two colours
for name, colour in (("Net export from Norway", COLORS["primary"]),
                     ("Net import to Norway", COLORS["accent"])):
    flow_fig.add_scattergeo(lat=[None], lon=[None], mode="lines", name=name,
                            line=dict(color=colour, width=4))
flow_fig.update_geos(
    projection_type="mercator", lonaxis_range=[-4, 31], lataxis_range=[52.5, 71.5],
    showland=True, landcolor="#f2f5f8", showocean=True, oceancolor="white",
    showcountries=True, countrycolor="#c6dbef", coastlinecolor="#c6dbef",
    showframe=False)
flow_fig.update_layout(height=560, margin=dict(l=0, r=0, t=10, b=0),
                       legend=dict(y=0.02, x=0.02, xanchor="left",
                                   yanchor="bottom"))
st.plotly_chart(flow_fig, theme=None)
st.caption(f"Net flow in {year} (TWh = export minus import). Thicker line = "
           "more electricity; the arrow points where the electricity goes. "
           "Hover a line for export and import.")

# Two columns: pie chart on the left, line plot on the right
left, right = st.columns(2)

# ---------- Left: pie chart for one year ----------
with left:
    st.subheader("One connection")
    connection = st.selectbox("Connection", connections, index=default_idx,
                              format_func=connection_label)

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
        title=f"{connection_label(connection)}, {year}", height=420, hovermode="closest",
        annotations=[dict(text=f"<b>{totals.sum():.2f}</b><br>TWh total",
                          showarrow=False, font=dict(size=16))],
        legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center",
                    yanchor="top"),
    )
    st.plotly_chart(fig, theme=None)
    if not totals.empty:
        exp, imp = totals.get("export", 0.0), totals.get("import", 0.0)
        st.caption(f"Through {connection_label(connection)}, Norway exported "
                   f"{exp:.2f} TWh and imported {imp:.2f} TWh in {year}.")
    csv_download(year_df.set_index("date"), f"flows_{connection}_{year}.csv")

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
            title=f"{connection_label(connection)}, {year}", height=420,
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
        "- **Zone codes:** SE1–SE4 = Swedish price areas, DK1 = western "
        "Denmark, DE_LU = Germany/Luxembourg (NordLink), NL = Netherlands "
        "(NorNed), GB = Great Britain (North Sea Link), FI = Finland.\n"
        "- **Default connection:** the first connection from the price area chosen "
        "in the sidebar."
    )
