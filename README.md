# IND320 – Norway's Water Battery

Streamlit app and Jupyter Notebooks for the IND320 project work (NMBU,
autumn 2026). The app combines weekly reservoir statistics from NVE,
hourly ERA5 weather data from open-meteo and cross-border electricity
flows from ENTSO-E (stored in MongoDB).

- **App:** https://ind320prosjektmaryan-lmvbjxajmrnrqkykq8ivne.streamlit.app/
- **Notebooks:** `notebooks/ind320_compulsory_1.ipynb`, `_2.ipynb`, `_3.ipynb`

## Structure
| File / folder | Content |
|---|---|
| `app.py` | Entry point: menu (`st.navigation`) and global area selector |
| `home.py` | Front page with key figures |
| `pages/` | Data Table, Plot, Reservoir Analysis, Weather Anomalies, Cross-border Flows |
| `utils.py` | Data loading with caching (NVE API, MongoDB, open-meteo) |
| `analysis.py` | SPC/DCT, LOF, STL and spectrogram functions |
| `theme.py` | Shared colour palette and plot style |
| `notebooks/` | Development and documentation for parts 1–3 |

## Run locally
1. `pip install -r requirements.txt`
2. Create `.streamlit/secrets.toml` with the MongoDB connection string:
   ```toml
   [mongo]
   uri = "mongodb+srv://..."
   ```
3. `streamlit run app.py`
