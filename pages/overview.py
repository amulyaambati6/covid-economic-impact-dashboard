
import streamlit as st


def show_overview():
    st.title("🌍 COVID-19 & the Global Economy")

    st.markdown(
        """
        ### How did the pandemic reshape the global economy?

        COVID-19 was more than a health crisis. It disrupted economic
        activity, affected employment, and contributed to changing
        inflation patterns around the world.

        Explore how these effects differed across countries and over time.
        """
    )

    st.divider()

    st.subheader("What will you explore?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📉 GDP Growth")
        st.write(
            "Compare economic contractions during the pandemic "
            "and recovery in the following years."
        )

    with col2:
        st.markdown("### 👥 Unemployment")
        st.write(
            "Explore how employment conditions changed "
            "across the selected countries."
        )

    with col3:
        st.markdown("### 💸 Inflation")
        st.write(
            "Track price changes before, during, and after "
            "the main pandemic period."
        )

    st.divider()

    st.subheader("Our scope")

    st.markdown(
        """
        - **7 countries:** Brazil, China, France, Germany, India,
          Rwanda, and the United States.
        - **Economic indicators:** 2018–2024.
        - **COVID-19 and policy indicators:** 2020–2022.
        """
    )

    st.info(
        "Ready to explore? Open **Dashboard & analysis** "
        "in the sidebar to discover the data and key findings."
    )
