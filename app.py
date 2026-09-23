"""Startpunkt for IND320-appen (denne filen kjøres av Streamlit).

app.py fungerer som "ruter": den bygger sidemenyen med st.navigation
og kjører siden brukeren har valgt. Selve innholdet ligger i egne filer:
  - home.py                 : forside
  - pages/1_Data_Table.py   : tabell med minigrafer
  - pages/2_Plot.py         : interaktivt plott
  - pages/3_Future_Work.py  : plassholder for senere deler
"""
import streamlit as st

# Felles oppsett for alle sider. initial_sidebar_state="expanded" sørger for
# at sidemenyen alltid er synlig når appen åpnes.
st.set_page_config(
    page_title="IND320 Reservoirs",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidene i menyen, med tydelige navn og ikoner
pages = [
    st.Page("home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/1_Data_Table.py", title="Data Table", icon="📊"),
    st.Page("pages/2_Plot.py", title="Plot", icon="📈"),
    st.Page("pages/3_Future_Work.py", title="Future Work", icon="⚙️"),
]

# Kort informasjon nederst i sidemenyen, synlig på alle sider
st.sidebar.caption("IND320 – Compulsory work 1\n\nData: data/reservoirs.csv")

# Lag menyen og kjør valgt side
st.navigation(pages).run()
