
import streamlit as st

from pages.overview import show_overview
from pages.home import show_home

st.set_page_config(
    page_title="COVID-19 and the Global Economy",
    page_icon="🌍",
    layout="wide",
)

st.sidebar.title("CentraleDigitalLab")
st.sidebar.caption("Data Storytelling · Team of four")
st.sidebar.markdown("**Presentation deadline:** October 21, 2026")

pages = [
    st.Page(
        show_overview,
        title="Project overview",
        icon="📘",
        default=True,
    ),
    st.Page(
        show_home,
        title="Dashboard & analysis",
        icon="📊",
    ),
]

selected_page = st.navigation(pages)
selected_page.run()
