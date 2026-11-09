"""Interactive plot with choice of area type, column and period.

The area type defaults to the one matching the global area selector in
the sidebar, and the selected area is drawn as a thick line.
"""
import io

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import streamlit as st

import theme  # noqa: F401  shared palette and plot style
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
marker = "o" if points_per_line <= 60 else None

fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")

# One line per area number; the area from the sidebar is emphasised
for number, area_df in subset.groupby("area_number"):
    label = area_label(area_type, number)
    selected = label == area or area_type == "NO"
    ax.plot(area_df["date"], area_df[choice] * scale, marker=marker,
            markersize=3, label=label,
            linewidth=2.5 if selected else 1,
            alpha=1 if selected else 0.6)

# Fixed y-axis based on all data for the area type, so periods compare
lo, hi = all_data[choice].min() * scale, all_data[choice].max() * scale
pad = (hi - lo) * 0.05 or 0.5
ax.set_ylim(lo - pad, hi + pad)
ax.set_ylabel(ylabel)

# Date axis that adapts to the length of the period
locator = mdates.AutoDateLocator()
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

ax.set_title(f"{name} – {start_month} to {end_month} "
             f"({AREA_TYPES[area_type]}, weekly)")
ax.set_xlabel("Date")
# The legend is placed below the plot, so it never covers the lines
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5, fontsize=9)

# Save the figure manually and show it as an image, so the plot keeps
# the same size when the period changes
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150)
st.image(buf)
plt.close(fig)  # free memory; Streamlit reruns the script on every change

st.caption(
    "Source: NVE Magasinstatistikk API. The thick line is the area chosen in "
    "the sidebar. The API response is cached for one hour."
)
