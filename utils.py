"""Felles hjelpefunksjoner for alle sidene i Streamlit-appen.

Data hentes bare ett sted, slik at alle sider bruker samme innlesing,
samme engelske kolonnenavn og samme caching.

Del 2: CSV-filen er erstattet med en direkte tilkobling til NVEs
Magasinstatistikk-API, og strømflyt over landegrensene leses fra MongoDB.
"""
import pandas as pd
import requests
import streamlit as st
from pymongo import MongoClient

# Adresse til NVEs åpne Magasinstatistikk-API (krever ingen nøkkel)
API_URL = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

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

# Måleverdier som kan velges i plottene. area_number, iso_year og iso_week er
# ikke med lenger: områdenummeret vises nå som egne linjer, og år/uke er tid.
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

# De tre områdetypene i API-et, med forklaring til radioknappene
AREA_TYPES = {
    "NO": "NO – whole of Norway",
    "EL": "EL – price areas NO1–NO5",
    "VASS": "VASS – river system regions 1–4",
}


def area_label(area_type: str, number: int) -> str:
    """Leselig navn på et område, f.eks. 'NO2' eller 'VASS3'."""
    if area_type == "NO":
        return "Norway"
    if area_type == "EL":
        return f"NO{number}"
    return f"VASS{number}"


@st.cache_data(ttl=3600)  # API-et kalles høyst én gang i timen; ellers brukes cache
def fetch_reservoirs() -> pd.DataFrame:
    """Henter all magasinstatistikk fra NVE-API-et og gir kolonnene engelske navn."""
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    df = pd.DataFrame(response.json()).rename(columns=RENAME)
    df["date"] = pd.to_datetime(df["date"])
    # Månedskolonne (f.eks. "1995-01") brukes til å velge perioder i appen
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df


def load_data(area_type: str = "NO", start_month: str | None = None,
              end_month: str | None = None) -> pd.DataFrame:
    """Data for én områdetype (NO, EL eller VASS), eventuelt bare for en periode.

    Resultatet er sortert etter område og dato. Uten periode returneres alt.
    """
    df = fetch_reservoirs()
    df = df[df["area_type"] == area_type]
    if start_month is not None and end_month is not None:
        # Månedene har formatet "ÅÅÅÅ-MM", så tekstsammenligning gir riktig rekkefølge
        df = df[(df["month"] >= start_month) & (df["month"] <= end_month)]
    return df.sort_values(["area_number", "date"]).reset_index(drop=True)


@st.cache_data(ttl=3600)
def load_flows() -> pd.DataFrame:
    """Daglig strømflyt over landegrensene, lagret i MongoDB fra Jupyter Notebook.

    Tilkoblingsstrengen leses fra st.secrets (lokalt: .streamlit/secrets.toml,
    på streamlit.io: Secrets i appens innstillinger), så den aldri havner på GitHub.
    """
    client = MongoClient(st.secrets["mongo"]["uri"])
    docs = list(client["ind320"]["flows_daily"].find({}, {"_id": 0}))
    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["connection", "direction", "date"]).reset_index(drop=True)