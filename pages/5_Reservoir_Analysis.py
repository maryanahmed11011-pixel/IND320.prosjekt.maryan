"""STL decomposition and spectrogram of the reservoir filling degree.

The area comes from the global selector in the sidebar (app.py).
"""
import matplotlib.pyplot as plt
import streamlit as st

from analysis import plot_spectrogram, stl_decompose
from utils import AREAS, filling_series

area = st.session_state.get("price_area", "NO3")
st.title(f"🔍 Reservoir analysis – {area}")
st.caption("Weekly filling degree from NVE Magasinstatistikk, 1995 until "
           "today. Change area in the sidebar.")

series = filling_series(area)
tab_stl, tab_spec = st.tabs(["STL decomposition", "Spectrogram"])

with tab_stl:
    st.info(
        "**What you see:** STL splits the filling degree into a slowly varying "
        "**trend** (wet and dry years), a repeating **seasonal** pattern "
        "(low in April, high in October) and a **residual** (what is left). "
        "Larger smoothers give smoother components; robust fit reduces the "
        "influence of unusual weeks. The trend at the very end is less "
        "reliable, since there is no later data to smooth with."
    )
    c1, c2, c3 = st.columns(3)
    # STL requires odd window lengths (step=2 from an odd start)
    seasonal = c1.slider("Seasonal smoother (weeks)", 7, 51, 13, step=2)
    trend = c2.slider("Trend smoother (weeks)", 53, 261, 105, step=2)
    robust = c3.checkbox("Robust fit", value=False)

    fig = stl_decompose(series, seasonal=seasonal, trend=trend,
                        robust=robust, label=f"Filling degree {area}")
    st.pyplot(fig)
    plt.close(fig)

with tab_spec:
    st.info(
        "**What you see:** how strong each cycle is over time. Bright colours "
        "mean strong cycles. The band at **1 cycle per year** is the annual "
        "snowmelt-and-drawdown cycle; weaker bands at 2 and 3 are harmonics. "
        "A longer window gives sharper frequencies but less detail in time."
    )
    c1, c2, c3 = st.columns(3)
    window = c1.slider("Window length (weeks)", 26, 260, 104, step=2)
    # Overlap must be smaller than the window length
    overlap = c2.slider("Window overlap (weeks)", 0, window - 1,
                        min(78, window - 1))
    max_freq = c3.slider("Max frequency (cycles/year)", 2, 26, 6)

    fig = plot_spectrogram(series, window_length=window,
                           overlap=overlap, max_freq=max_freq,
                           label=f"Filling degree {area}")
    st.pyplot(fig)
    plt.close(fig)
