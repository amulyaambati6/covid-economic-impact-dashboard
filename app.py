
from functools import wraps
from pathlib import Path

import streamlit as st

from pages.country_comparison import show_country_comparison
from pages.economic_growth import show_economic_growth
from pages.home import show_home
from pages.inflation import show_inflation
from pages.key_findings import show_key_findings
from pages.labour_market import show_labour_market
from pages.landing import show_landing
from pages.overview import show_overview
from pages.policy_response import show_policy_response
from src.visualizations.layout import RESEARCH_PAGES, apply_styles

ROOT = Path(__file__).parent

st.set_page_config(
    page_title="COVID-19 and the Global Economy",
    page_icon="🦠",
    layout="wide",
)

# Brand mark at the top of the sidebar (and a small icon when collapsed).
st.logo(
    str(ROOT / "assets" / "logo.svg"),
    icon_image=str(ROOT / "assets" / "logo_icon.svg"),
    size="large",
)

# Project CSS on top of the theme in .streamlit/config.toml.
STYLE_FILE = ROOT / "assets" / "style.css"


def with_style(page_function):
    """Add the CSS inside each page, so it also applies after a refresh."""
    @wraps(page_function)  # keeps the function name for Streamlit
    def run_page():
        if STYLE_FILE.exists():
            apply_styles(STYLE_FILE.read_text(encoding="utf-8"))
        page_function()
    return run_page


# Page functions for the six research pages, matched to the shared registry
# (src/visualizations/layout.py) that also builds the homepage cards.
RESEARCH_FUNCTIONS = {
    "growth": (show_economic_growth, ":material/trending_up:"),
    "labour": (show_labour_market, ":material/groups:"),
    "inflation": (show_inflation, ":material/payments:"),
    "policy": (show_policy_response, ":material/policy:"),
    "comparison": (show_country_comparison, ":material/public:"),
    "findings": (show_key_findings, ":material/lightbulb:"),
}

pages = {
    "": [
        st.Page(with_style(show_landing), title="Home", icon=":material/home:",
                url_path="home", default=True),
    ],
    "Research": [
        st.Page(
            with_style(RESEARCH_FUNCTIONS[page["key"]][0]),
            title=page["title"],
            icon=RESEARCH_FUNCTIONS[page["key"]][1],
            url_path=page["url_path"],
        )
        for page in RESEARCH_PAGES
    ],
    "Reference": [
        st.Page(with_style(show_home), title="Full report (one page)",
                icon=":material/article:", url_path="full-report"),
        st.Page(with_style(show_overview), title="About & methods",
                icon=":material/info:", url_path="about"),
    ],
}

selected_page = st.navigation(pages)
selected_page.run()
