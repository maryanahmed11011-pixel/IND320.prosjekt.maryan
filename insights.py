"""Small helpers that make the pages easier to read (part 4, extra).

- reservoir_status / status_sentence: the newest week of one area compared
  with last year and with the normal (median of all earlier years), as
  numbers and as one plain sentence shown at the top of the pages.
- seasonal_figure: this year's filling on top of the historical range
  (min-max band and median) for the same week numbers.
- csv_download: a download button for the data behind a plot or table.

The data functions only use pandas, so they can be tested without Streamlit.
"""
import pandas as pd


def weekly_normal(area_df: pd.DataFrame, before_year: int) -> pd.DataFrame:
    """Min, median and max filling (%) per ISO week over all years before
    `before_year`. area_df holds one area (columns iso_year, iso_week,
    filling_degree as a share 0-1)."""
    history = area_df[area_df["iso_year"] < before_year]
    return (history.groupby("iso_week")["filling_degree"]
            .agg(["min", "median", "max"]) * 100)


def reservoir_status(area_df: pd.DataFrame, upto=None) -> dict:
    """Numbers for the newest week (or the newest week up to `upto`).

    Returns the filling (%), the week and year, the change since last week,
    and the difference (percentage points) to the same week last year and
    to the normal for this week. Missing comparisons are None.
    """
    df = area_df.dropna(subset=["filling_degree"]).sort_values("date")
    if upto is not None:
        df = df[df["date"] <= pd.Timestamp(upto)]
    if df.empty:
        return {}
    latest = df.iloc[-1]
    year, week = int(latest["iso_year"]), int(latest["iso_week"])
    value = latest["filling_degree"] * 100

    prev_week = df.iloc[-2]["filling_degree"] * 100 if len(df) > 1 else None
    last_year = df[(df["iso_year"] == year - 1) & (df["iso_week"] == week)]
    normal = weekly_normal(df, year)
    first_year = int(df["iso_year"].min())
    return {
        "date": latest["date"], "year": year, "week": week, "value": value,
        "week_change": None if prev_week is None else value - prev_week,
        "vs_last_year": (None if last_year.empty
                         else value - last_year["filling_degree"].iloc[0] * 100),
        "normal": normal["median"].get(week),
        "vs_normal": (None if week not in normal.index
                      else value - normal["median"][week]),
        "normal_period": f"{first_year}–{year - 1}",
    }


def status_sentence(name: str, s: dict) -> str:
    """One plain-language sentence (markdown) for a reservoir_status dict."""
    if not s:
        return f"No reservoir data for {name}."
    text = (f"**{name}** is **{s['value']:.1f} %** full in week "
            f"{s['week']}, {s['year']}")
    if s["vs_normal"] is not None:
        diff = s["vs_normal"]
        if abs(diff) < 2:
            text += " – about **normal** for this time of year"
        else:
            word = "above" if diff > 0 else "below"
            text += f" – **{abs(diff):.1f} pp {word} normal** for this week"
    if s["vs_last_year"] is not None and abs(s["vs_last_year"]) < 0.5:
        text += ", and about the same as a year ago"
    elif s["vs_last_year"] is not None:
        word = "higher" if s["vs_last_year"] > 0 else "lower"
        text += f", and {abs(s['vs_last_year']):.1f} pp {word} than a year ago"
    if s["week_change"] is not None:
        trend = "rising" if s["week_change"] > 0 else "falling"
        text += f". The level is {trend} ({s['week_change']:+.1f} pp in the last week)"
    return text + "."


def seasonal_figure(area_df: pd.DataFrame, name: str):
    """Plotly figure: this year and last year on top of the historical
    min-max band and median for each week number."""
    import plotly.graph_objects as go
    from theme import COLORS

    df = area_df.dropna(subset=["filling_degree"]).sort_values("date")
    year = int(df["iso_year"].iloc[-1])
    band = weekly_normal(df, year)
    this_year = df[df["iso_year"] == year]
    prev_year = df[df["iso_year"] == year - 1]

    fig = go.Figure()
    # Historical range as a filled band: the max line is filled down to the
    # min line ("tonexty")
    fig.add_scatter(x=band.index, y=band["min"], mode="lines",
                    line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=band.index, y=band["max"], mode="lines",
                    line=dict(width=0), fill="tonexty",
                    fillcolor="rgba(158, 202, 225, 0.5)",  # COLORS["light"]
                    name=f"Range {int(df['iso_year'].min())}–{year - 1}",
                    hoverinfo="skip")
    fig.add_scatter(x=band.index, y=band["median"], mode="lines",
                    name="Normal (median)",
                    line=dict(color=COLORS["primary"], dash="dash"),
                    hovertemplate="%{y:.1f} %")
    fig.add_scatter(x=prev_year["iso_week"], y=prev_year["filling_degree"] * 100,
                    mode="lines", name=str(year - 1),
                    line=dict(color=COLORS["neutral"]),
                    hovertemplate="%{y:.1f} %")
    fig.add_scatter(x=this_year["iso_week"], y=this_year["filling_degree"] * 100,
                    mode="lines+markers", name=str(year),
                    line=dict(color=COLORS["dark"], width=3),
                    marker=dict(size=5), hovertemplate="%{y:.1f} %")
    fig.update_layout(title=f"{name}: {year} compared with earlier years",
                      xaxis=dict(title="Week number", range=[1, 53]),
                      yaxis=dict(title="Filling degree (%)", range=[0, 100]),
                      height=420, hovermode="x unified")
    return fig


def csv_download(df: pd.DataFrame, filename: str, label: str = "Download data (CSV)"):
    """Download button for the data behind a plot or table."""
    import streamlit as st
    st.download_button(f"⬇️ {label}", df.to_csv().encode("utf-8"),
                       file_name=filename, mime="text/csv")
