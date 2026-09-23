"""Side 2: Tabell med én rad per datakolonne og minigraf for første måned."""
import pandas as pd
import streamlit as st

from utils import MEASURE_COLS, load_data  # felles innlesing med caching

st.set_page_config(page_title="Data Table", page_icon="📊", layout="wide")
st.title("📊 Data Table")

df = load_data()

# Finn første måned i datasettet og plukk ut radene (ukene) i den måneden
first_month = df["month"].iloc[0]
first_month_df = df[df["month"] == first_month]

st.write(
    f"One row per column in the imported data. The mini chart shows the "
    f"weekly values in the first month of the data ({first_month})."
)

# Bygg en ny tabell der hver kolonne fra CSV-filen blir én rad.
# Kolonnen "first_month" inneholder en liste med tall, som
# LineChartColumn tegner som en liten linjegraf i hver rad.
rows = []
for col in MEASURE_COLS:
    rows.append(
        {
            "column": col,
            "first_month": first_month_df[col].tolist(),
            "min": df[col].min(),
            "mean": df[col].mean(),
            "max": df[col].max(),
        }
    )
table = pd.DataFrame(rows)

st.dataframe(
    table,
    column_config={
        "column": "Data column",
        "first_month": st.column_config.LineChartColumn(
            f"First month ({first_month})", width="medium"
        ),
        "min": st.column_config.NumberColumn("Min (all data)", format="%.3f"),
        "mean": st.column_config.NumberColumn("Mean (all data)", format="%.3f"),
        "max": st.column_config.NumberColumn("Max (all data)", format="%.3f"),
    },
    hide_index=True,
)

# Vis også de første radene av selve dataene
st.subheader("Raw data (first rows)")
st.dataframe(df.head(20), hide_index=True)
