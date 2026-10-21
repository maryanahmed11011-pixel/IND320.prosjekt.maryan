"""Side 2: Tabell med én rad per område og minigraf for første måned."""
import pandas as pd
import streamlit as st

from utils import AREA_TYPES, MEASURE_COLS, UNITS, area_label, load_data

st.title("📊 Data Table")

# Radioknapper: hvilken områdetype som skal vises (NO, EL eller VASS)
area_type = st.radio(
    "Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, horizontal=True
)
# Hvilken måleverdi minigrafene skal vise
measure = st.selectbox("Column", MEASURE_COLS, format_func=lambda c: f"{c} – {UNITS[c]}")

df = load_data(area_type)

# Én rad per områdenummer. Kolonnen "first_month" inneholder en liste med tall,
# som LineChartColumn tegner som en liten linjegraf i hver rad.
rows = []
for number, area_df in df.groupby("area_number"):
    first_month = area_df["month"].iloc[0]
    first_month_df = area_df[area_df["month"] == first_month]
    rows.append(
        {
            "area": area_label(area_type, number),
            "period": f"{area_df['date'].min():%Y-%m-%d} – {area_df['date'].max():%Y-%m-%d}",
            "first_month": first_month_df[measure].tolist(),
            "min": round(float(area_df[measure].min()), 3),
            "mean": round(float(area_df[measure].mean()), 3),
            "max": round(float(area_df[measure].max()), 3),
        }
    )
table = pd.DataFrame(rows)

st.write(
    f"One row per area of type **{area_type}**. The data is weekly, so the mini chart "
    f"shows the weekly values of **{measure}** in the first month of data for each area."
)

st.dataframe(
    table,
    column_config={
        "area": "Area",
        "period": "Data period",
        "first_month": st.column_config.LineChartColumn("First month", width="medium"),
        "min": st.column_config.NumberColumn("Min (all data)"),
        "mean": st.column_config.NumberColumn("Mean (all data)"),
        "max": st.column_config.NumberColumn("Max (all data)"),
    },
    hide_index=True,
)

# Vis også de første radene av selve dataene, med datoer uten klokkeslett
st.subheader("Raw data (first rows)")
st.dataframe(
    df.drop(columns="month").head(20),
    column_config={"date": st.column_config.DateColumn("date", format="YYYY-MM-DD")},
    hide_index=True,
)
st.caption("Source: NVE Magasinstatistikk API (fetched live, cached for one hour).")
