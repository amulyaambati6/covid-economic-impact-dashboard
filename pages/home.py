"""Landing page with clearly marked placeholders for future analyses."""
import streamlit as st


def show_home() -> None:
    """Render the project introduction and planned analysis sections."""
    st.title("COVID-19 and the Global Economy")
    st.subheader("CentraleDigitalLab Data Storytelling")
    st.markdown("**Research question:** How did COVID-19 impact the global economy?")
    st.write(
        "We are preparing a country comparison for 2019–2023. The dates and "
        "country selection remain subject to data validation."
    )

    st.info(
        "This is a project scaffold. No charts or research findings are shown "
        "until the team validates the data."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("### Economic indicators")
        st.write("Planned: GDP growth, unemployment, and inflation.")
        st.caption("Placeholder: validated economic indicator charts will go here.")
    with right:
        st.markdown("### Pandemic indicators")
        st.write("Planned: COVID-19 cases, deaths, and possibly response stringency.")
        st.caption("Placeholder: validated pandemic charts will go here.")

    st.markdown("### Country comparison")
    st.write("Candidate countries: USA, India, France, China, Brazil, Germany, and Rwanda.")
    st.caption("Final country and indicator selections require team agreement and coverage checks.")