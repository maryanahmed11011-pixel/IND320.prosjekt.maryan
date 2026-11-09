"""Shared colour palette and plot style for the whole app.

Every page and plot imports its colours from here, so the app has one
consistent "water" look. The same blue is used as primaryColor in
.streamlit/config.toml, so widgets match the plots.

Importing this module also applies the matplotlib style below.
"""
import matplotlib.pyplot as plt
from cycler import cycler

# ---------- Palette ----------
COLORS = {
    "primary": "#3182bd",   # main blue: data lines, export, buttons
    "dark": "#08306b",      # dark blue: import, titles, current year, text
    "light": "#9ecae1",     # light blue: ranges and bands
    "pale": "#deebf7",      # very light blue: backgrounds
    "accent": "#f28e2b",    # warm orange: contrast colour for extra lines
    "alert": "#d62728",     # red: outliers and anomalies
    "neutral": "#8c8c8c",   # grey: limits, last year, helper lines
}

# Colours for several lines in one plot (e.g. NO1-NO5): blues first,
# then contrasting colours, so all lines can be told apart
LINE_COLORS = ["#08306b", "#3182bd", "#6baed6", "#f28e2b", "#2ca25f"]

# Cross-border directions: both blue, import darker (and dashed in line plots)
DIRECTION_COLORS = {"export": COLORS["primary"], "import": COLORS["dark"]}

# ---------- Matplotlib style ----------
plt.rcParams.update({
    "axes.prop_cycle": cycler(color=LINE_COLORS),
    "axes.edgecolor": "#c6dbef",
    "axes.labelcolor": COLORS["dark"],
    "axes.titlecolor": COLORS["dark"],
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#c6dbef",
    "grid.linestyle": "--",
    "grid.alpha": 0.6,
    "xtick.color": COLORS["dark"],
    "ytick.color": COLORS["dark"],
    "legend.frameon": False,
    "font.size": 10,
    "figure.facecolor": "white",
})
