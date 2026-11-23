"""Shared colour palette and plot style for the whole app.

Every page and plot imports its colours from here, so the app has one
consistent "water" look. The same blue is used as primaryColor in
.streamlit/config.toml, so widgets match the plots.

Importing this module registers a Plotly template ("ind320") and makes it
the default, so all Plotly figures in the app get the same style. In the
app, figures are shown with st.plotly_chart(fig, theme=None), so
Streamlit's own chart theme does not override the template.
The matplotlib style is kept for static plots in the notebooks.
"""
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
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

# Colours of the menu groups (app.py), as in the sketch in the notebook
GROUP_COLORS = {
    "Overview": "#3182bd",   # blue
    "Explore": "#2ca25f",    # green
    "Analyse": "#f28e2b",    # orange
    "Predict": "#08306b",    # dark blue
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


# ---------- Plotly template (dynamic plots in the app) ----------
_AXIS = dict(
    gridcolor="#c6dbef", griddash="dash", linecolor="#c6dbef",
    zeroline=False, ticks="outside", tickcolor="#c6dbef",
    title=dict(font=dict(color=COLORS["dark"])),
)
pio.templates["ind320"] = go.layout.Template(layout=dict(
    colorway=LINE_COLORS,
    font=dict(family="sans-serif", size=13, color=COLORS["dark"]),
    title=dict(font=dict(size=16, color=COLORS["dark"]), x=0.01),
    paper_bgcolor="white",
    plot_bgcolor="white",
    xaxis=_AXIS,
    yaxis=_AXIS,
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                yanchor="bottom", y=1.02, xanchor="right", x=1),
    hoverlabel=dict(bgcolor="white", bordercolor=COLORS["primary"]),
    hovermode="x unified",
    margin=dict(l=60, r=20, t=60, b=50),
    colorscale=dict(sequential="Blues"),
))
pio.templates.default = "plotly_white+ind320"
