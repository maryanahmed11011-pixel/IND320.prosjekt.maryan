"""Entry point for the IND320 app (this file is run by Streamlit).

app.py works as a router: it builds the sidebar menu with st.navigation,
holds the global area selector, and runs the selected page. The content
of each page lives in its own file:
  - home.py                        : front page with key figures
  - pages/7_Map.py                 : interactive map, click selects area (part 4)
  - pages/8_Correlation.py         : sliding window correlation (part 4)
  - pages/9_Forecast.py            : reservoir forecast with River (part 4)
  - pages/1_Reservoir_Data.py      : table with mini charts + plot (part 4)
  - pages/3_Exchange_Rates.py      : EUR/USD from Norges Bank (part 4)
  - pages/5_Reservoir_Analysis.py  : STL and spectrogram (part 3)
  - pages/6_Weather_Anomalies.py   : SPC and LOF on ERA5 data (part 3)
  - pages/4_Cross_Border.py        : cross-border flows (MongoDB)
"""
import streamlit as st

from theme import GROUP_COLORS
from utils import AREAS

st.set_page_config(
    page_title="IND320 Reservoirs",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Pages grouped by type of task, as in the sketch in the part 4 notebook:
# Overview -> Explore (the data sources) -> Analyse -> Predict
pages = {
    "Overview": [
        st.Page("home.py", title="Home", icon="🏠", default=True),
        st.Page("pages/7_Map.py", title="Map", icon="🗺️"),
    ],
    "Explore": [
        st.Page("pages/1_Reservoir_Data.py", title="Reservoir Data", icon="📊"),
        st.Page("pages/4_Cross_Border.py",
                title="Cross-border Flows", icon="🔌"),
        st.Page("pages/3_Exchange_Rates.py", title="Exchange Rates", icon="💱"),
    ],
    "Analyse": [
        st.Page("pages/5_Reservoir_Analysis.py",
                title="Reservoir Analysis", icon="🔍"),
        st.Page("pages/6_Weather_Anomalies.py",
                title="Weather Anomalies", icon="🌦️"),
        st.Page("pages/8_Correlation.py",
                title="Weather vs. Reservoirs", icon="🔗"),
    ],
    "Predict": [
        st.Page("pages/9_Forecast.py", title="Reservoir Forecast", icon="🔮"),
    ],
}

# Global selector: one area for the whole app. The key stores the choice
# in st.session_state, so it persists when switching pages. Each page
# reads it and uses it as its default (area type, connection, weather).
# A click on the map sets "pending_area"; it is applied here, before the
# widget is created, since a widget's value cannot change after that.
st.session_state.setdefault("price_area", "NO3")
if "pending_area" in st.session_state:
    st.session_state["price_area"] = st.session_state.pop("pending_area")
st.sidebar.selectbox(
    "Area", list(AREAS), key="price_area",
    format_func=AREAS.get,
    help="Sets the default area on all pages: reservoir data, "
         "weather data and the matching cross-border connection. "
         "Can also be set by clicking an area on the map.",
)

st.sidebar.caption(
    "IND320 – Compulsory work 4\n\n"
    "Data: NVE Magasinstatistikk API, ENTSO-E (via MongoDB), "
    "open-meteo (ERA5) and Norges Bank"
)

page = st.navigation(pages)

# Each menu group has its own colour (theme.GROUP_COLORS). The active
# page's link in the menu and a small label above the page title get the
# colour of its group, so it is clear which part of the app is active.
group = next(name for name, items in pages.items()
             if any(p.title == page.title for p in items))
colour = GROUP_COLORS[group]
# Short description of each group, shown in the banner over the title
GROUP_TEXT = {
    "Overview": "Key figures and the map",
    "Explore": "The data sources",
    "Analyse": "Patterns, anomalies and relationships",
    "Predict": "Forecasting",
}
# (no indentation inside the HTML: Markdown would show indented lines as code)
css = (
    f'[data-testid="stSidebarNavLink"][aria-current="page"] '
    f"{{background: {colour}26; border-left: 4px solid {colour};}}"
    f" .group-banner {{background: {colour}1A; border-left: 6px solid {colour};"
    f" border-radius: 6px; padding: 0.45rem 0.9rem; margin-bottom: 0.4rem;}}"
    f" .group-banner b {{color: {colour}; font-size: 1.05rem;"
    f" letter-spacing: 0.06em; text-transform: uppercase;}}"
    f" .group-banner span {{color: #4a4a4a; font-size: 0.95rem;"
    f" margin-left: 0.6rem;}}"
)
st.markdown(f'<style>{css}</style><div class="group-banner"><b>{group}</b>'
            f'<span>{GROUP_TEXT[group]}</span></div>', unsafe_allow_html=True)
page.run()
