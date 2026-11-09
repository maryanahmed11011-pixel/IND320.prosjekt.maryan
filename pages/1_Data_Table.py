"""Table with one row per area and a mini chart of the first month.

The area type defaults to the one matching the global area selector in
the sidebar (EL for NO1-NO5, VASS for VASS1-3).
"""
import pandas as pd
import streamlit as st

from utils import AREA_TYPES, MEASURE_COLS, UNITS, area_label, load_data

st.title("📊 Data Table")

# Default area type from the global selector (app.py)
area = st.session_state.get("price_area", "NO3")
default_type = "VASS" if area.startswith("VASS") else "EL"

# Radio buttons: which area type to show (NO, EL or VASS)
area_type = st.radio(
    "Area type", list(AREA_TYPES), format_func=AREA_TYPES.get,
    index=list(AREA_TYPES).index(default_type), horizontal=True,
)
# Which measure the mini charts show
measure = st.selectbox("Column", MEASURE_COLS,
                       format_func=lambda c: UNITS[c])

df = load_data(area_type)

# One row per area number. "first_month" holds a list of numbers, which
# LineChartColumn draws as a small line chart in each row.
rows = []
for number, area_df in df.groupby("area_number"):
    first_month = area_df["month"].iloc[0]
    first_month_df = area_df[area_df["month"] == first_month]
    rows.append({
        "area": area_label(area_type, number),
        "period": f"{area_df['date'].min():%Y-%m-%d} – "
                  f"{area_df['date'].max():%Y-%m-%d}",
        "first_month": first_month_df[measure].tolist(),
        "min": round(float(area_df[measure].min()), 3),
        "mean": round(float(area_df[measure].mean()), 3),
        "max": round(float(area_df[measure].max()), 3),
    })
table = pd.DataFrame(rows)

st.write(
    f"One row per area of type **{area_type}**. The data is weekly, so the mini "
    f"chart shows the weekly values of **{UNITS[measure].lower()}** in the first "
    f"month of data for each area. The area chosen in the sidebar is marked ▶."
)

# Mark the area chosen in the global selector
table["area"] = table["area"].where(table["area"] != area, "▶ " + area)

st.dataframe(
    table,
    column_config={
        "area": "Area",
        "period": "Data period",
        "first_month": st.column_config.LineChartColumn("First month",
                                                        width="medium"),
        "min": st.column_config.NumberColumn("Min (all data)"),
        "mean": st.column_config.NumberColumn("Mean (all data)"),
        "max": st.column_config.NumberColumn("Max (all data)"),
    },
    hide_index=True,
)

# Also show the first rows of the raw data, with dates without time
with st.expander("Raw data (first rows)"):
    st.dataframe(
        df.drop(columns="month").head(20),
        column_config={"date": st.column_config.DateColumn("date",
                                                           format="YYYY-MM-DD")},
        hide_index=True,
    )
st.caption("Source: NVE Magasinstatistikk API (fetched live, cached for one hour).")
