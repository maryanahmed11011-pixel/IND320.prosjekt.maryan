"""Exchange rates from Norges Bank (part 4).

EUR and USD against NOK from Norges Bank's open API (fetch_exchange_rates
in analysis.py, the same function as in the notebook). The rates exist on
Norwegian business days only; the weekly view uses the same Sunday weeks
as Magasinstatistikk, so it can be compared with the reservoir data.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import daily_to_weekly
from theme import COLORS
from insights import csv_download
from utils import load_exchange_rates

CURRENCY_COLORS = {"EUR": COLORS["dark"], "USD": COLORS["accent"]}

st.title("💱 Exchange Rates")
st.caption("EUR and USD against NOK from Norges Bank. Rates are published "
           "on Norwegian business days, around 16:00.")

# ---------- Controls ----------
this_year = pd.Timestamp.today().year
c1, c2, c3 = st.columns([2, 2, 1])
start_year, end_year = c1.select_slider(
    "Years", options=list(range(2000, this_year + 1)),
    value=(this_year - 4, this_year), key="fx_years")
currencies = c2.multiselect("Currencies", ["EUR", "USD"],
                            default=["EUR", "USD"], key="fx_currencies")
resolution = c3.radio("Resolution", ["Daily", "Weekly"], index=1,
                      key="fx_resolution",
                      help="Weekly = mean of the business days in each week "
                           "ending on Sunday, as for the reservoir data.")
if not currencies:
    st.info("Choose at least one currency.")
    st.stop()

# ---------- Data ----------
try:
    daily = load_exchange_rates(start_year)
except Exception as err:  # API down or no connection
    st.error("Could not download exchange rates from Norges Bank. Please try "
             f"again later.\n\nDetails: {err}")
    st.stop()

daily = daily[daily.index.year <= end_year][currencies].dropna(how="all")
if daily.empty:
    st.warning("No exchange rates for the chosen years.")
    st.stop()
rates = daily_to_weekly(daily).dropna(how="all") if resolution == "Weekly" else daily

# ---------- Key numbers ----------
cols = st.columns(len(currencies))
for col, cur in zip(cols, currencies):
    series = daily[cur].dropna()
    col.metric(f"{cur}/NOK, {series.index[-1]:%d %b %Y}", f"{series.iloc[-1]:.3f}",
               f"{series.iloc[-1] - series.iloc[0]:+.3f} since "
               f"{series.index[0]:%d %b %Y}", delta_color="off")

# The conclusion in one sentence: a higher rate means a weaker krone
parts = []
for cur in currencies:
    series = daily[cur].dropna()
    change = (series.iloc[-1] / series.iloc[0] - 1) * 100
    word = "weaker" if change > 0 else "stronger"
    parts.append(f"one {'euro' if cur == 'EUR' else 'US dollar'} costs "
                 f"**{abs(change):.1f} % {'more' if change > 0 else 'less'}** "
                 f"(the krone is {word} against {cur})")
st.info(f"Since {daily.index[0]:%d %b %Y}, " + "; ".join(parts) + ".", icon="💡")

# ---------- Plot ----------
fig = go.Figure()
for cur in currencies:
    fig.add_scatter(x=rates.index, y=rates[cur], mode="lines", name=cur,
                    line=dict(color=CURRENCY_COLORS[cur], width=1.6),
                    hovertemplate=f"{cur}: %{{y:.3f}} NOK<extra></extra>")
fig.update_layout(
    title=f"{' and '.join(currencies)} against NOK "
          f"({resolution.lower()}, {start_year}–{end_year})",
    yaxis_title="NOK per unit", height=450,
)
st.plotly_chart(fig, theme=None)

with st.expander("Data table"):
    st.dataframe(rates.round(4).sort_index(ascending=False)
                 .rename_axis("Week (Sunday)" if resolution == "Weekly" else "Date"))
    csv_download(rates, f"exchange_rates_{resolution.lower()}_{start_year}_{end_year}.csv")

with st.expander("About the data"):
    st.markdown(
        "- **Source:** Norges Bank's open SDMX API (series `B.EUR+USD.NOK.SP`), "
        "no key needed; downloaded with the same function as in the notebook "
        "and cached for six hours.\n"
        "- **Time:** one value per Norwegian business day, a snapshot taken at "
        "14:15 CET. Weekends, public holidays and Christmas Eve have no rate.\n"
        "- **Use in the app:** the weekly means can be chosen as exogenous "
        "variables on the forecasting page."
    )
