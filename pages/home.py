"""Full report: every research page on one scrolling page.

This keeps the original single-page dashboard available (useful for
printing or scrolling through in a presentation). It reuses the research
page functions, so its charts and numbers are identical to theirs.
"""

import streamlit as st

from pages.country_comparison import render_country_comparison
from pages.economic_growth import render_economic_growth
from pages.inflation import render_inflation
from pages.key_findings import render_key_findings
from pages.labour_market import render_labour_market
from pages.policy_response import render_policy_response
from src.visualizations.layout import (
    load_data_or_stop,
    require_countries,
    sidebar_filters,
)

SECTIONS = [
    render_economic_growth,
    render_labour_market,
    render_inflation,
    render_policy_response,
    render_country_comparison,
]


def show_home():
    data = load_data_or_stop()
    countries, years = sidebar_filters(data["countries"])
    require_countries(countries)

    st.caption(
        "All six research pages on one page. Filters in the sidebar apply to "
        "every section except Key Findings, which always covers all seven countries."
    )
    for render in SECTIONS:
        render(data, countries, years)
        st.divider()
    render_key_findings(data)


if __name__ == "__main__":
    show_home()
