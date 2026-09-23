"""Side 1: Forside med kort beskrivelse og lenker."""
import streamlit as st

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
- Streamlit app: https://ind320prosjektmaryan-lmvbjxajmrnrqkykq8ivne.streamlit.app/
"""
)
