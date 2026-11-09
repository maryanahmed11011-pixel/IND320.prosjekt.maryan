"""Entry point for the IND320 app (this file is run by Streamlit).

app.py works as a router: it builds the sidebar menu with st.navigation,
holds the global area selector, and runs the selected page. The content
of each page lives in its own file:
  - home.py                        : front page with key figures
  - pages/1_Data_Table.py          : table with mini charts
  - pages/2_Plot.py                : interactive reservoir plot
  - pages/5_Reservoir_Analysis.py  : STL and spectrogram (part 3)
  - pages/6_Weather_Anomalies.py   : SPC and LOF on ERA5 data (part 3)
  - pages/4_Cross_Border.py        : cross-border flows (MongoDB)
"""
import streamlit as st

from utils import AREAS

st.set_page_config(
    page_title="IND320 Reservoirs",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Pages grouped by topic
pages = {
    "Overview": [
        st.Page("home.py", title="Home", icon="🏠", default=True),
    ],
    "Reservoirs": [
        st.Page("pages/1_Data_Table.py", title="Data Table", icon="📊"),
        st.Page("pages/2_Plot.py", title="Plot", icon="📈"),
        st.Page("pages/5_Reservoir_Analysis.py",
                title="Reservoir Analysis", icon="🔍"),
    ],
    "Weather": [
        st.Page("pages/6_Weather_Anomalies.py",
                title="Weather Anomalies", icon="🌦️"),
    ],
    "Power exchange": [
        st.Page("pages/4_Cross_Border.py",
                title="Cross-border Flows", icon="🔌"),
    ],
}

# Global selector: one area for the whole app. The key stores the choice
# in st.session_state, so it persists when switching pages. Each page
# reads it and uses it as its default (area type, connection, weather).
st.sidebar.selectbox(
    "Area", list(AREAS), index=2, key="price_area",
    format_func=AREAS.get,
    help="Sets the default area on all pages: reservoir data, "
         "weather data and the matching cross-border connection.",
)

st.sidebar.caption(
    "IND320 – Compulsory work 3\n\n"
    "Data: NVE Magasinstatistikk API, ENTSO-E (via MongoDB) "
    "and open-meteo (ERA5)"
)

st.navigation(pages).run()
