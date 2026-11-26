"""Reservoir data: overview table and interactive plot on one page (part 4).

In part 4 the former pages "Data Table" (LineChartColumn) and "Plot" are
joined into one data overview page with two tabs, as planned in the
sketch. The area type is chosen once at the top and used by both tabs;
it defaults to the type of the area chosen in the sidebar or on the map
(EL for NO1-NO5, VASS for VASS1-3).
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import theme  # noqa: F401  shared palette and Plotly template
from insights import csv_download, reservoir_status, seasonal_figure, status_sentence
from utils import AREA_TYPES, MEASURE_COLS, UNITS, area_label, load_data

# Columns stored as a share (0-1) are shown in percent in the plot
PERCENT_COLS = {"filling_degree", "filling_degree_prev_week",
                "filling_degree_change"}

st.title("📊 Reservoir Data")
st.caption("Weekly data from NVE Magasinstatistikk: an overview table with "
           "mini charts, and an interactive plot for a chosen period.")

# Default area type from the global selector (app.py)
area = st.session_state.get("price_area", "NO3")
default_type = "VASS" if area.startswith("VASS") else "EL"

# Shared by both tabs: which area type to show (NO, EL or VASS)
area_type = st.radio(
    "Area type", list(AREA_TYPES), format_func=AREA_TYPES.get,
    index=list(AREA_TYPES).index(default_type), horizontal=True,
)

try:
    all_data = load_data(area_type)
except Exception as err:  # NVE API down or no connection
    st.error("Could not load data from the NVE Magasinstatistikk API. Please "
             f"try again later.\n\nDetails: {err}")
    st.stop()

tab_normal, tab_table, tab_plot = st.tabs(
    ["📅 This year vs normal", "📋 Overview table", "📈 Plot"])

# ---------- Tab 0: one area compared with its own history ----------
with tab_normal:
    numbers = sorted(all_data["area_number"].unique())
    labels = [area_label(area_type, n) for n in numbers]
    one = st.selectbox("Area", labels,
                       index=labels.index(area) if area in labels else 0,
                       key="normal_area")
    area_df = all_data[all_data["area_number"] == numbers[labels.index(one)]]
    st.info(status_sentence(one, reservoir_status(area_df)), icon="💡")
    st.plotly_chart(seasonal_figure(area_df, one), theme=None)
    st.caption("The light band is the lowest and highest filling for each "
               "week in earlier years, the dashed line the normal (median). "
               "pp = percentage points.")


# ---------- Tab 1: one row per area with a mini chart ----------
with tab_table:
    measure = st.selectbox("Column", MEASURE_COLS,
                           format_func=lambda c: UNITS[c], key="table_measure")

    # One row per area number. "first_month" holds a list of numbers,
    # which LineChartColumn draws as a small line chart in each row.
    rows = []
    for number, area_df in all_data.groupby("area_number"):
        first_month = area_df["month"].iloc[0]
        first_month_df = area_df[area_df["month"] == first_month]
        rows.append({
            "area": area_label(area_type, number),
            "period": f"{area_df['date'].min():%Y-%m-%d} – "
                      f"{area_df['date'].max():%Y-%m-%d}",
            "first_month": first_month_df[measure].tolist(),
            "min": round(float(area_df[measure].min()), 3),
            "mean": round(float(area_df[measure].mean()), 3),
            "max": round(float(area_df[measure].max()), 3),
        })
    table = pd.DataFrame(rows)

    st.write(
        f"One row per area of type **{area_type}**. The data is weekly, so the "
        f"mini chart shows the weekly values of **{UNITS[measure].lower()}** in "
        f"the first month of data for each area. The area chosen in the "
        f"sidebar is marked ▶."
    )
    # Mark the area chosen in the global selector
    table["area"] = table["area"].where(table["area"] != area, "▶ " + area)

    st.dataframe(
        table,
        column_config={
            "area": "Area",
            "period": "Data period",
            "first_month": st.column_config.LineChartColumn("First month",
                                                            width="medium"),
            "min": st.column_config.NumberColumn("Min (all data)"),
            "mean": st.column_config.NumberColumn("Mean (all data)"),
            "max": st.column_config.NumberColumn("Max (all data)"),
        },
        hide_index=True,
    )
    csv_download(all_data.drop(columns="month").set_index("date"),
                 f"reservoirs_{area_type}.csv", "Download all data (CSV)")
    # Also show the first rows of the raw data, with dates without time
    with st.expander("Raw data (first rows)"):
        st.dataframe(
            all_data.drop(columns="month").head(20),
            column_config={"date": st.column_config.DateColumn(
                "date", format="YYYY-MM-DD")},
            hide_index=True,
        )

# ---------- Tab 2: interactive plot for a chosen period ----------
with tab_plot:
    choice = st.selectbox("Column", MEASURE_COLS,
                          format_func=lambda c: UNITS[c], key="plot_measure")

    # Readable name and unit, e.g. "Filling degree" and "%"
    name = UNITS[choice].split(" (")[0]
    scale = 100 if choice in PERCENT_COLS else 1
    ylabel = f"{name} (%)" if scale == 100 else UNITS[choice]

    # The slider selects which period is shown (default: last 5 years)
    months = sorted(all_data["month"].unique().tolist())
    default_start = months[-60] if len(months) >= 60 else months[0]
    start_month, end_month = st.select_slider(
        "Select period to load", options=months,
        value=(default_start, months[-1]))
    subset = load_data(area_type, start_month, end_month)

    # Point markers only when there are few points per line
    points_per_line = len(subset) / max(subset["area_number"].nunique(), 1)
    mode = "lines+markers" if points_per_line <= 60 else "lines"

    fig = go.Figure()
    # One line per area number; the area from the sidebar is emphasised
    for number, area_df in subset.groupby("area_number"):
        label = area_label(area_type, number)
        selected = label == area or area_type == "NO"
        fig.add_scatter(
            x=area_df["date"], y=area_df[choice] * scale, mode=mode,
            name=label, line=dict(width=3 if selected else 1.3),
            marker=dict(size=4), opacity=1 if selected else 0.6,
            hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
        )

    # Fixed y-axis based on all data for the area type, so periods compare
    lo, hi = all_data[choice].min() * scale, all_data[choice].max() * scale
    pad = (hi - lo) * 0.05 or 0.5
    fig.update_layout(
        title=f"{name} – {start_month} to {end_month} "
              f"({AREA_TYPES[area_type]}, weekly)",
        xaxis_title="Date", yaxis=dict(title=ylabel, range=[lo - pad, hi + pad]),
        height=470,
    )
    st.plotly_chart(fig, theme=None)
    st.caption("The thick line is the area chosen in the sidebar.")
    csv_download(subset.drop(columns="month").set_index("date"),
                 f"reservoirs_{area_type}_{start_month}_{end_month}.csv",
                 "Download the plotted period (CSV)")

st.caption("Source: NVE Magasinstatistikk API (fetched live, cached for one hour).")
