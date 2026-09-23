"""Felles hjelpefunksjoner for alle sidene i Streamlit-appen.

Data leses bare ett sted, slik at alle sider bruker samme
innlesing, samme engelske kolonnenavn og samme caching.
"""
import pandas as pd
import streamlit as st

# Oversettelse fra originale (norske) kolonnenavn til engelske, forklarende navn
RENAME = {
    "dato_Id": "date",
    "omrType": "area_type",
    "omrnr": "area_number",
    "iso_aar": "iso_year",
    "iso_uke": "iso_week",
    "fyllingsgrad": "filling_degree",
    "kapasitet_TWh": "capacity_TWh",
    "fylling_TWh": "filling_TWh",
    "neste_Publiseringsdato": "next_publication_date",
    "fyllingsgrad_forrige_uke": "filling_degree_prev_week",
    "endring_fyllingsgrad": "filling_degree_change",
}

# Måleverdiene som er meningsfulle å vise i tabell og plott
MEASURE_COLS = [
    "filling_degree",
    "capacity_TWh",
    "filling_TWh",
    "filling_degree_prev_week",
    "filling_degree_change",
]

# Enhet for hver måleverdi, brukes som aksetittel i plottene
UNITS = {
    "filling_degree": "Filling degree (share, 0-1)",
    "capacity_TWh": "Capacity (TWh)",
    "filling_TWh": "Stored energy (TWh)",
    "filling_degree_prev_week": "Filling degree last week (share, 0-1)",
    "filling_degree_change": "Weekly change in filling degree",
}


@st.cache_data  # Filen leses bare én gang; senere kall hentes fra cache
def load_data(path: str = "data/reservoirs.csv") -> pd.DataFrame:
    """Leser CSV-filen og returnerer én tidsserie for hele Norge."""
    df = pd.read_csv(path)
    df = df.rename(columns=RENAME)
    df["date"] = pd.to_datetime(df["date"])

    # Filen inneholder flere områdetyper (NO = hele landet, EL = strømområder,
    # VASS = vassdragsregioner). Vi bruker bare totalen for Norge ("NO"),
    # slik at vi får én ukentlig tidsserie. Radene sorteres etter dato.
    df = df[df["area_type"] == "NO"].sort_values("date").reset_index(drop=True)

    # Månedskolonne (f.eks. "1995-01") brukes til å velge måneder i appen
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df
