"""Hjemmeside for IND320-appen.

Streamlit lager sidemenyen automatisk: app.py blir hjemmesiden,
og hver .py-fil i mappen pages/ blir en egen side i menyen.
"""
import streamlit as st

# Sideoppsett må stå før alt annet Streamlit-innhold
st.set_page_config(page_title="IND320 Reservoirs", page_icon="💧", layout="wide")

st.title("💧 Norwegian Water Reservoirs")
st.subheader("IND320 – Compulsory work 1")

st.markdown(
    """
This app shows weekly filling levels for Norwegian hydropower reservoirs
(national total, 1995 until today), read from `data/reservoirs.csv`.

**Use the sidebar menu on the left to navigate:**
- **Data Table** – one row per data column, with a mini line chart of the first month
- **Plot** – interactive plot with column selection and month range
- **Future Work** – placeholder for later parts of the project

**Links**
- GitHub repository: https://github.com/maryanahmed11011-pixel/IND320.prosjekt.maryan
"""
)
