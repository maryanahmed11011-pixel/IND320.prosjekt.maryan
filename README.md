# IND320 – Hydropower Reservoirs in Norway

Streamlit app and Jupyter Notebooks for the IND320 project work (NMBU,
autumn 2026). The app combines weekly reservoir statistics from NVE,
hourly ERA5 weather data from open-meteo, cross-border electricity flows
from ENTSO-E (stored in MongoDB) and exchange rates from Norges Bank.


- **App:** https://ind320prosjektmaryan-lmvbjxajmrnrqkykq8ivne.streamlit.app/
- **Screencast (part 3):** https://github.com/maryanahmed11011-pixel/IND320-screencasts/blob/main/screencast_del3.mp4
- **Notebooks:** `notebooks/ind320_compulsory_1.ipynb`, `_2.ipynb`, `_3.ipynb`, `_4.ipynb`

## Structure
| File / folder | Content |
|---|---|
| `app.py` | Entry point: menu in four groups (`st.navigation`), group colours and global area selector |
| `home.py` | Front page with key figures and shortcuts |
| `pages/` | Overview: Map · Explore: Reservoir Data, Cross-border Flows, Exchange Rates · Analyse: Reservoir Analysis, Weather Anomalies, Weather vs. Reservoirs · Predict: Reservoir Forecast |
| `utils.py` | Data loading with caching (NVE API, MongoDB, open-meteo, Norges Bank) |
| `analysis.py` | Shared functions for the app and notebooks: areas, time alignment, exchange rates, SPC/DCT, LOF, STL, spectrogram, correlation, forecasting (River) |
| `theme.py` | Shared colour palette, Plotly template and group colours |
| `geo/` | NVE shapefiles (price areas, NVE regions) and the GeoJSON files for the map |
| `notebooks/` | Development and documentation for parts 1–4 |

## Run locally
1. `pip install -r requirements.txt`
2. Create `.streamlit/secrets.toml` with the MongoDB connection string:
   ```toml
   [mongo]
   uri = "mongodb+srv://..."
   ```
3. `streamlit run app.py`
