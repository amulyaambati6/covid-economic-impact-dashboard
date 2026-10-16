"""Project overview page."""
import streamlit as st


def show_overview() -> None:
    """Explain the research plan and the next validation steps."""
    st.title("Project overview")
    st.markdown("**Research question:** How did COVID-19 impact the global economy?")
    st.write(
        "The initial study period is 2019–2023. The team will validate source "
        "coverage and comparability before choosing the final countries and measures."
    )

    st.markdown("### Planned workflow")
    st.markdown(
        "1. Review the economic indicator coverage audit.\n"
        "2. Validate COVID-19 source definitions, coverage, and missingness.\n"
        "3. Agree on a focused comparison and document limitations.\n"
        "4. Add analysis, charts, and storytelling after the data are validated."
    )
    st.warning("Coverage gaps and failed requests must remain distinguishable; missing values are not zero.")