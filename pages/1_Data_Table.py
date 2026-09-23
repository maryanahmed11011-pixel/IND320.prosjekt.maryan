"""Side 2: Tabell med én rad per datakolonne og minigraf for første måned."""
import pandas as pd
import streamlit as st

from utils import load_data  # felles innlesing med caching

st.title("📊 Data Table")

df = load_data()

# Finn første måned i datasettet og plukk ut radene (ukene) i den måneden
first_month = df["month"].iloc[0]
first_month_df = df[df["month"] == first_month]

st.write(
       f"One row per column in the imported data. The data is weekly, so the mini chart "
       f"shows the {len(first_month_df)} weekly values in the first month ({first_month})."
   )

st.caption(
    "Text and date columns (date, area_type, next_publication_date) are not shown, "
    "since they cannot be drawn as line charts."
)

# Én rad per tallkolonne i dataene. Tekst- og datokolonner kan ikke vises
# som linjegraf og er utelatt. Kolonnen "first_month" inneholder en liste
# med tall, som LineChartColumn tegner som en liten linjegraf i hver rad.
numeric_cols = df.select_dtypes("number").columns.tolist()

rows = []
for col in numeric_cols:
    rows.append(
        {
            "column": col,
            "first_month": first_month_df[col].tolist(),
            # Avrunding gir ryddige tall uten unødvendige desimaler (f.eks. 1995, ikke 1995.000)
            "min": round(float(df[col].min()), 3),
            "mean": round(float(df[col].mean()), 3),
            "max": round(float(df[col].max()), 3),
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
st.caption("next_publication_date = 0001-01-01 means that no date is registered.")
