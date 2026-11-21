"""Interactive plot with choice of area type, column and period.

The area type defaults to the one matching the global area selector in
the sidebar, and the selected area is drawn as a thick line.
"""
import plotly.graph_objects as go
import streamlit as st

import theme  # noqa: F401  shared palette and Plotly template
from utils import AREA_TYPES, MEASURE_COLS, UNITS, area_label, load_data

# Columns stored as a share (0-1) are shown in percent
PERCENT_COLS = {"filling_degree", "filling_degree_prev_week",
                "filling_degree_change"}

st.title("📈 Reservoir Plot")

# Default area type from the global selector (app.py)
area = st.session_state.get("price_area", "NO3")
default_type = "VASS" if area.startswith("VASS") else "EL"

# Radio buttons: area type. The plot gets one line per area number.
area_type = st.radio(
    "Area type", list(AREA_TYPES), format_func=AREA_TYPES.get,
    index=list(AREA_TYPES).index(default_type), horizontal=True,
)
choice = st.selectbox("Select column", MEASURE_COLS,
                      format_func=lambda c: UNITS[c])

# Readable name and unit, e.g. "Filling degree" and "%"
name = UNITS[choice].split(" (")[0]
scale = 100 if choice in PERCENT_COLS else 1
ylabel = f"{name} (%)" if scale == 100 else UNITS[choice]

# All available months for the selected area type
all_data = load_data(area_type)
months = sorted(all_data["month"].unique().tolist())

# The slider selects which period is loaded (default: last 5 years)
default_start = months[-60] if len(months) >= 60 else months[0]
start_month, end_month = st.select_slider(
    "Select period to load", options=months, value=(default_start, months[-1])
)
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
        x=area_df["date"], y=area_df[choice] * scale, mode=mode, name=label,
        line=dict(width=3 if selected else 1.3),
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
# Fixed height and full width, so the plot keeps its size when the period
# changes. Zoom, pan and hover come with Plotly.
st.plotly_chart(fig, theme=None)

st.caption(
    "Source: NVE Magasinstatistikk API. The thick line is the area chosen in "
    "the sidebar. The API response is cached for one hour."
)
