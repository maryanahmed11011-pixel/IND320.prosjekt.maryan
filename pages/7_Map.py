"""Interactive map of the Magasinstatistikk areas (part 4).

- Outlines of the price areas (NO1–NO5) or water areas (VASS1–3), from
  the GeoJSON files converted from NVE's shapefiles (geo/ folder).
- The areas are coloured (transparently) by reservoir filling or by a
  weather property for the week chosen with the time controls.
- A click on an area selects it: the outline gets thicker and orange, and
  the choice is stored as the global area in the sidebar, so all other
  pages follow. The chosen week is stored in st.session_state["map_week"].

The map uses folium (Leaflet) through streamlit-folium. With Plotly, every
change of the figure made Streamlit draw the whole chart again, so the map
disappeared for a moment on each click. Here the base map is built once and
only the coloured areas are sent as a layer that is swapped in place
(feature_group_to_add), so the map stays visible.
"""
import copy

import branca.colormap as cm
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from theme import COLORS
from utils import (AREAS, NVE, area_label, load_data, load_geojson,
                   load_or_stop, load_weather_weekly)

LAYERS = {"price": "Price areas (NO1–NO5)", "water": "Water areas (VASS1–3)"}
MODES = {
    "price": "Reservoir filling – price areas",
    "water": "Reservoir filling – water areas",
    "weather": "Weather property",
}
# Fixed colour ranges, so the colours mean the same in every week
WEATHER = {
    "temperature_2m": ("Temperature", "°C", -20, 20),
    "precipitation": ("Precipitation (weekly sum)", "mm", 0, 100),
    "wind_speed_10m": ("Wind speed", "km/h", 0, 40),
    "relative_humidity_2m": ("Relative humidity", "%", 50, 100),
}

# The app uses the wide layout; on this page the content is kept narrower,
# so the map does not fill the whole screen
st.markdown("<style>.block-container {max-width: 1100px;}</style>",
            unsafe_allow_html=True)

st.title("🗺️ Map")
st.caption("Click an area to select it for the whole app. Colours show the "
           "chosen week; data from NVE Magasinstatistikk and open-meteo (ERA5).")

# ---------- What to show ----------
c1, c2, c3 = st.columns([2, 2, 2])
mode = c1.selectbox("Colour by", list(MODES), format_func=MODES.get,
                    key="map_mode")
if mode == "weather":
    var = c2.selectbox("Weather property", list(WEATHER),
                       format_func=lambda v: WEATHER[v][0],
                       key="map_weather_var")
    # Weather can be shown for either area type; default follows the
    # area chosen in the sidebar
    selected_area = st.session_state.get("price_area", "NO3")
    layer = c3.radio("Areas", list(LAYERS), format_func=LAYERS.get,
                     index=1 if selected_area.startswith("VASS") else 0,
                     key="map_layer")
else:
    layer = mode

# ---------- Time: the weeks of Magasinstatistikk (dated on Sundays) ----------
area_type = "EL" if layer == "price" else "VASS"
filling = load_or_stop(NVE, load_data, area_type)
weeks = sorted(pd.to_datetime(filling["date"].unique()))
if mode == "weather":
    # ERA5 is downloaded per year from 2000 (as on the weather page) and
    # lags a few days behind today
    newest = pd.Timestamp.today().normalize() - pd.Timedelta(days=6)
    weeks = [w for w in weeks if 2000 <= w.year and w <= newest]

# The widgets get fixed keys and their start values are put in
# session_state *before* they are created, and only when needed. Passing a
# new value= on every run made Streamlit recreate the slider after each
# click, so the handle jumped to another week.
# "map_week" is shared with other pages and survives page changes (the
# widget keys are removed by Streamlit when you leave the page).
if pd.Timestamp(st.session_state.get("map_week", weeks[-1])) not in weeks:
    st.session_state["map_week"] = weeks[-1]
shared_week = pd.Timestamp(st.session_state.get("map_week", weeks[-1]))

years = sorted({w.year for w in weeks}, reverse=True)
if st.session_state.get("map_year") not in years:
    st.session_state["map_year"] = shared_week.year
t1, t2 = st.columns([1, 4])
year = t1.selectbox("Year", years, key="map_year")

year_weeks = [w for w in weeks if w.year == year]
if st.session_state.get("map_week_slider") not in year_weeks:
    # first visit, or a new year was chosen
    st.session_state["map_week_slider"] = (shared_week if shared_week in year_weeks
                                           else year_weeks[-1])
week = t2.select_slider(
    "Week (ending Sunday)", options=year_weeks, key="map_week_slider",
    format_func=lambda d: f"Week {d.isocalendar().week} · {d:%d %b %Y}",
)
st.session_state["map_week"] = week  # shared with other pages

# ---------- Values per area for the chosen week ----------
geojson = load_or_stop("the GeoJSON files in geo/", load_geojson, layer,
                       hint="Check that the geo/ folder is in the repository.")
features = geojson["features"]
regions = [f["properties"]["region"] for f in features]

if mode in ("price", "water"):
    this_week = filling[filling["date"] == week]
    values = {area_label(area_type, n): v * 100 for n, v in
              zip(this_week["area_number"], this_week["filling_degree"])}
    title, unit, vmin, vmax = "Filling degree", "%", 0, 100
    colormap = cm.LinearColormap(
        ["#f7fbff", "#9ecae1", "#3182bd", "#08306b"], vmin=vmin, vmax=vmax)
else:
    title, unit, vmin, vmax = WEATHER[var]
    values = {}
    try:
        for region in regions:
            weekly = load_weather_weekly(region, week.year)
            if week in weekly.index:
                values[region] = weekly.loc[week, var]
    except Exception as err:  # e.g. rate limit (HTTP 429) from open-meteo
        st.error("Could not download weather data from open-meteo. The free "
                 "API may be rate limited – please try again in a minute."
                 f"\n\nDetails: {err}")
        st.stop()
    if var == "temperature_2m":
        # Blue below 0 °C, white at 0 °C, red above
        colormap = cm.LinearColormap(["#2166ac", "#f7f7f7", "#b2182b"],
                                     index=[vmin, 0, vmax], vmin=vmin, vmax=vmax)
    else:
        colormap = cm.LinearColormap(["#f7fbff", "#6baed6", "#08306b"],
                                     vmin=vmin, vmax=vmax)
colormap.caption = f"{title} ({unit})"
no_data = all(pd.isna(values.get(r)) for r in regions)


def legend_html():
    """Colour legend drawn by Streamlit under the map (not inside the map,
    where it covered the +/- zoom buttons and made the map redraw)."""
    stops = [colormap(vmin + (vmax - vmin) * i / 10) for i in range(11)]
    ticks = "".join(f"<span>{vmin + (vmax - vmin) * i / 4:g}</span>"
                    for i in range(5))
    return (f'<div style="max-width:420px;font-size:13px">'
            f'<b>{title} ({unit})</b>'
            f'<div style="height:12px;border:1px solid #ccc;margin-top:4px;'
            f'background:linear-gradient(to right,{",".join(stops)})"></div>'
            f'<div style="display:flex;justify-content:space-between">'
            f'{ticks}</div></div>')


selected = st.session_state.get("price_area", "NO3")


def fill_colour(value):
    """Colour for a value; grey if missing, clipped to the colour range."""
    if value is None or pd.isna(value):
        return "#bdbdbd"
    return colormap(min(max(value, vmin), vmax))


# ---------- Base map: identical on every run, so it is drawn only once ----
# No background tiles: only Norway's areas on a white background.
# (zoom with +/- or double-click; scroll-zoom is off so the page scrolls)
base = folium.Map(location=[65.0, 15.5], zoom_start=4, tiles=None,
                  scrollWheelZoom=False, control_scale=False)
# White background, and no black focus box around a clicked area
base.get_root().header.add_child(folium.Element(
    "<style>.leaflet-container {background: #ffffff;}"
    " .leaflet-interactive:focus {outline: none;}</style>"))
base.fit_bounds([[57.8, 4.0], [71.3, 31.2]])  # mainland Norway
# The legend is NOT added to the base map: then the base map is identical
# in every week and mode, so streamlit-folium never has to redraw it

# ---------- Layer with the areas: swapped in place on every run ----------
areas_layer = folium.FeatureGroup(name="areas")
shown = copy.deepcopy(geojson)
for f in shown["features"]:
    v = values.get(f["properties"]["region"])
    f["properties"]["value"] = ("no data" if v is None or pd.isna(v)
                                else f"{v:.1f} {unit}")

folium.GeoJson(
    shown,
    style_function=lambda f: {
        "fillColor": fill_colour(values.get(f["properties"]["region"])),
        "fillOpacity": 0.6,
        # The selected area gets a thick outline in the contrast colour
        "color": COLORS["accent"] if f["properties"]["region"] == selected
        else COLORS["dark"],
        "weight": 4 if f["properties"]["region"] == selected else 1,
    },
    highlight_function=lambda f: {"weight": 3, "fillOpacity": 0.8},
    tooltip=folium.GeoJsonTooltip(fields=["region", "value"],
                                  aliases=["Area", title]),
).add_to(areas_layer)

# Name of each area at a point inside it (clicks pass through to the area)
for f in features:
    p = f["properties"]
    colour = COLORS["accent"] if p["region"] == selected else COLORS["dark"]
    folium.Marker(
        [p["lat"], p["lon"]],
        icon=folium.DivIcon(
            icon_size=(60, 20), icon_anchor=(30, 10),
            html=(f'<div style="pointer-events:none;text-align:center;'
                  f'font-weight:700;font-size:13px;color:{colour};'
                  f'text-shadow:0 0 3px white">{p["region"]}</div>')),
    ).add_to(areas_layer)

left, right = st.columns([3, 2], gap="large")
with left:
    result = st_folium(
        base, key=f"map_{layer}", height=560, use_container_width=True,
        feature_group_to_add=areas_layer,
        # Only clicks trigger a rerun (not panning or zooming)
        returned_objects=["last_active_drawing", "last_object_clicked"],
    )
    st.markdown(legend_html(), unsafe_allow_html=True)

# Only a *change* in the clicked area counts, so an old click does not
# override a later choice in the sidebar. The sidebar widget already
# exists in this run, so the value is passed on via "pending_area" and
# applied in app.py before the widget is created on the next run.
def clicked_region(result):
    """Region of the clicked area: the area that contains the clicked
    position (fallback: the properties of the clicked GeoJSON feature)."""
    point = result.get("last_object_clicked") if result else None
    if point:
        from shapely.geometry import Point, shape
        where = Point(point["lng"], point["lat"])
        for f in features:
            if shape(f["geometry"]).contains(where):
                return f["properties"]["region"]
    drawing = (result or {}).get("last_active_drawing") or {}
    region = drawing.get("properties", {}).get("region")
    return region if region in regions else None


# Each click has a new position, so the position tells whether this is a
# new click. An old click therefore never overrides a later choice in the
# sidebar, and clicking the same area again also works. The sidebar widget
# already exists in this run, so the value is passed on via "pending_area"
# and applied in app.py before the widget is created on the next run.
point = (result or {}).get("last_object_clicked")
click_id = (point["lat"], point["lng"]) if point else None
seen_key = f"map_seen_{layer}"
if click_id is not None and click_id != st.session_state.get(seen_key):
    st.session_state[seen_key] = click_id
    clicked = clicked_region(result)
    if clicked and clicked != selected:
        st.session_state["pending_area"] = clicked
        st.rerun()

# ---------- Details for the selected area ----------
with right:
    st.subheader(selected)
    st.caption(AREAS.get(selected, ""))
    # Shown here and not above the map: a message that comes and goes
    # above the map moves it on the page, and then Streamlit draws it again
    if no_data:
        st.info("No data for the chosen week. Try another week.")
    if selected in values and pd.notna(values[selected]):
        st.metric(f"{title}, week {week.isocalendar().week} {week.year}",
                  f"{values[selected]:.1f} {unit}")
    elif selected not in regions:
        st.info(f"{selected} is not shown in this layer. Switch area type "
                "or click an area on the map.")
    ranking = pd.Series(values, dtype=float).dropna().sort_values(ascending=False)
    if not ranking.empty:
        st.dataframe(ranking.round(1).rename(f"{title} ({unit})")
                     .rename_axis("Area"))
    st.page_link("pages/6_Weather_Anomalies.py", label="Weather anomalies",
                 icon="🌦️")
    st.page_link("pages/5_Reservoir_Analysis.py", label="Reservoir analysis",
                 icon="🔍")

with st.expander("About the map"):
    st.markdown(
        "- **Areas:** NVE's shapefiles for *Budområder* (price areas) and "
        "*NVE_Region* (water areas: East = RØ + RS, West = RV, North = "
        "RM + RN), converted to simplified GeoJSON in the part 4 notebook.\n"
        "- **Reservoir filling:** weekly values from Magasinstatistikk, "
        "dated on the Sunday that ends the ISO week.\n"
        "- **Weather:** ERA5 from open-meteo, averaged over 5 random points "
        "per area, converted from UTC to local days and aggregated to the "
        "same weeks (precipitation summed, the rest averaged). The colour "
        "scales are fixed, so weeks can be compared.\n"
        "- **Selection:** a click stores the area in the sidebar selector, "
        "so all pages follow. The chosen week is kept when you return."
    )
