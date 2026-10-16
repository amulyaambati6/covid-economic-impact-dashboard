"""Streamlit entry point for the COVID-19 economy storytelling project."""
import streamlit as st

from pages.home import show_home
from pages.overview import show_overview

st.set_page_config(
    page_title="COVID-19 and the Global Economy",
    page_icon="🌍",
    layout="wide",
)

st.sidebar.title("CentraleDigitalLab")
st.sidebar.caption("Data Storytelling · Team of four")
st.sidebar.markdown("**Presentation deadline:** October 21, 2026")

# Keep navigation and page content in small modules students can edit separately.
pages = [
    st.Page(show_home, title="Home", icon="🏠", default=True),
    st.Page(show_overview, title="Project overview", icon="📋"),
]
selected_page = st.navigation(pages)
selected_page.run()