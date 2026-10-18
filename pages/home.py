
"""Interactive dashboard and analysis of COVID-19's economic impact."""

import pandas as pd
import streamlit as st

from src.data.loader import load_monthly_data, load_annual_data, load_economic_data
from src.visualizations.charts import (
    plot_gdp_growth,
    plot_inflation,
    plot_unemployment,
    plot_covid_cases,
    plot_covid_deaths,
    plot_stringency,
    plot_covid_economic_relationship,
    plot_health_economic_relationship,
)


def _median_for_year(df, column, year):
    """Return the median indicator value for a given year."""
    subset = df.loc[df["year"] == year, column].dropna()
    return float(subset.median()) if not subset.empty else None


def _show_change_finding(df, column, label):
    """Summarize changes between 2019 and 2020 for selected countries."""
    pivot = df[df["year"].isin([2019, 2020])].pivot_table(
        index="country",
        columns="year",
        values=column,
        aggfunc="mean",
    )

    if 2019 not in pivot.columns or 2020 not in pivot.columns:
        st.info(f"Insufficient 2019–2020 data to compare {label.lower()}.")
        return

    changes = (pivot[2020] - pivot[2019]).dropna()

    if changes.empty:
        st.info(f"No comparable {label.lower()} observations.")
        return

    largest_increase = changes.idxmax()
    largest_decrease = changes.idxmin()

    left, right = st.columns(2)
    left.metric(
        f"Largest increase in {label.lower()}",
        largest_increase,
        f"{changes[largest_increase]:+.2f} percentage points",
    )
    right.metric(
        f"Largest decrease in {label.lower()}",
        largest_decrease,
        f"{changes[largest_decrease]:+.2f} percentage points",
    )


def show_home() -> None:
    st.title("COVID-19 and the Global Economy")
    st.markdown(
        "Explore how economic performance, pandemic outcomes, and "
        "government responses evolved across seven selected countries."
    )
    st.markdown(
        "**Research question:** How did the COVID-19 pandemic impact "
        "the global economy?"
    )

    try:
        monthly_df = load_monthly_data()
        annual_df = load_annual_data()

        gdp_df = load_economic_data("gdp_growth_pct")
        inflation_df = load_economic_data("inflation_pct")
        unemployment_df = load_economic_data("unemployment_pct")

    except (FileNotFoundError, OSError, ValueError) as error:
        st.error(f"Could not load the project datasets: {error}")
        return

    # Use one shared list of countries for all dashboard sections.
    country_sets = [
        set(df["country"].dropna().unique())
        for df in [monthly_df, annual_df, gdp_df, inflation_df, unemployment_df]
    ]
    countries = sorted(set.intersection(*country_sets))

    st.sidebar.header("Dashboard filters")
    selected_countries = st.sidebar.multiselect(
        "Select countries",
        options=countries,
        default=countries,
        key="selected_countries",
    )

    if not selected_countries:
        st.warning("Select at least one country to display the analysis.")
        return

    # All charts and calculations use the same selection.
    monthly = monthly_df[
        monthly_df["country"].isin(selected_countries)
    ].copy()

    annual = annual_df[
        annual_df["country"].isin(selected_countries)
    ].copy()

    gdp = gdp_df[gdp_df["country"].isin(selected_countries)].copy()
    inflation = inflation_df[
        inflation_df["country"].isin(selected_countries)
    ].copy()
    unemployment = unemployment_df[
        unemployment_df["country"].isin(selected_countries)
    ].copy()

    st.caption(
        f"Currently comparing {len(selected_countries)} of {len(countries)} "
        "countries. Economic trends cover 2018–2024; monthly pandemic "
        "and government-response indicators cover 2020–2022."
    )

    # ---------------------------------------------------------
    # 1. Economic impact
    # ---------------------------------------------------------
    st.header("1. Economic impact")
    st.write(
        "Did GDP growth contract in 2020? How did inflation and "
        "unemployment evolve before, during, and after the pandemic?"
    )

    gdp_2020 = gdp[gdp["year"] == 2020]["gdp_growth_pct"].dropna()
    inflation_2020 = inflation[
        inflation["year"] == 2020
    ]["inflation_pct"].dropna()
    inflation_2022 = inflation[
        inflation["year"] == 2022
    ]["inflation_pct"].dropna()

    k1, k2, k3 = st.columns(3)
    k1.metric(
        "Median GDP growth, 2020",
        f"{gdp_2020.median():.1f}%" if not gdp_2020.empty else "N/A",
    )
    k2.metric(
        "Median inflation, 2020",
        f"{inflation_2020.median():.1f}%"
        if not inflation_2020.empty else "N/A",
    )
    k3.metric(
        "Median inflation, 2022",
        f"{inflation_2022.median():.1f}%"
        if not inflation_2022.empty else "N/A",
    )

    st.subheader("GDP growth: pre-pandemic baseline and recovery")
    st.write(
        "Compare 2018–2019 with the contraction in 2020 and the "
        "subsequent recovery through 2024."
    )
    plot_gdp_growth(gdp)

    st.subheader("Inflation: changes in price growth")
    plot_inflation(inflation)

    st.subheader("Unemployment: labour-market changes")
    plot_unemployment(unemployment)

    with st.expander("Compare unemployment between 2019 and 2020"):
        _show_change_finding(
            unemployment, "unemployment_pct", "Unemployment"
        )

    # ---------------------------------------------------------
    # 2. COVID-19 outcomes
    # ---------------------------------------------------------
    st.divider()
    st.header("2. COVID-19 outcomes")
    st.write(
        "Compare monthly reported cases and deaths per million people. "
        "Reported figures may not be equally complete across countries."
    )

    left, right = st.columns(2)
    with left:
        plot_covid_cases(monthly)
    with right:
        plot_covid_deaths(monthly)

    deaths_2020_2022 = monthly.copy()
    deaths_2020_2022["year"] = pd.to_datetime(
        deaths_2020_2022["month"], errors="coerce"
    ).dt.year
    deaths_2020_2022 = deaths_2020_2022[
        deaths_2020_2022["year"].between(2020, 2022)
    ]

    mortality_summary = (
        deaths_2020_2022.groupby("country")["new_deaths_per_million"]
        .sum(min_count=1)
        .dropna()
        .sort_values(ascending=False)
    )

    if not mortality_summary.empty:
        st.subheader("Reported mortality across selected countries")
        st.dataframe(
            mortality_summary.rename(
                "Sum of monthly deaths per million (2020–2022)"
            ).reset_index(),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            "This sum is a descriptive comparison of monthly rates; "
            "it is not presented as an independently verified cumulative "
            "death rate."
        )

    # ---------------------------------------------------------
    # 3. Government response
    # ---------------------------------------------------------
    st.divider()
    st.header("3. Government response")
    st.write(
        "The stringency index summarizes the strictness of selected "
        "government policies. It does not directly measure compliance "
        "or policy effectiveness."
    )
    plot_stringency(monthly)

    if "sti_weighted" in monthly.columns:
        stringency = monthly.copy()
        stringency["year"] = pd.to_datetime(
            stringency["month"], errors="coerce"
        ).dt.year

        yearly_stringency = (
            stringency.groupby(["country", "year"])["sti_weighted"]
            .mean()
            .reset_index()
        )

        st.subheader("Average stringency by country and year")
        st.dataframe(
            yearly_stringency.pivot(
                index="country",
                columns="year",
                values="sti_weighted",
            ).round(1),
            use_container_width=True,
        )

    
# ---------- HEALTH AND ECONOMIC RELATIONSHIPS ----------
    st.header("How was the economy associated with the pandemic?")
    st.markdown(
    """
    These charts compare health and policy indicators with economic
    outcomes. Each point represents one country in one year.

    Use the country colours and hover over points to compare countries
    and years. These are associations, not proof of causation.
    """
        )

    st.subheader("1. COVID-19 deaths and economic growth")
    plot_health_economic_relationship(
    annual,
    health_column="new_deaths_per_million",
    economic_column="gdp_growth_pct",
    title="Reported COVID-19 deaths vs. GDP growth",
    health_label="Annual deaths per million",
    economic_label="GDP growth (%)",
    )

    st.caption(
    "Research question: were higher reported death rates associated "
    "with weaker GDP growth? Check how the annual death-rate values "
    "were aggregated before interpreting this chart."
    )

    st.divider()

    st.subheader("2. COVID-19 cases and unemployment")
    plot_health_economic_relationship(
    annual,
    health_column="new_cases_per_million",
    economic_column="unemployment_pct",
    title="Reported COVID-19 cases vs. unemployment",
    health_label="Annual cases per million",
    economic_label="Unemployment rate (%)",
    )

    st.caption(
    "Research question: did countries with more reported cases also "
    "experience higher unemployment? The annual comparison cannot "
    "show the exact timing of monthly changes."
    ) 

    st.divider()

    st.subheader("3. Government restrictions and economic growth")
    plot_health_economic_relationship(
    annual,
    health_column="sti_weighted",
    economic_column="gdp_growth_pct",
    title="Government stringency vs. GDP growth",
    health_label="Weighted stringency index",
    economic_label="GDP growth (%)",
    )

    st.caption(
    "Research question: was stricter government policy associated "
    "with weaker economic growth? Policy stringency may also have "
    "responded to worsening health conditions."
    )

    st.divider()

    st.subheader("4. COVID-19 deaths and unemployment")
    plot_health_economic_relationship(
    annual,
    health_column="new_deaths_per_million",
    economic_column="unemployment_pct",
    title="Reported COVID-19 deaths vs. unemployment",
    health_label="Annual deaths per million",
    economic_label="Unemployment rate (%)",
    )

    st.divider()

    st.subheader("5. Government restrictions and inflation")
    plot_health_economic_relationship(
        annual,
        health_column="sti_weighted",
        economic_column="inflation_pct",
        title="Government stringency vs. inflation",
        health_label="Weighted stringency index",
        economic_label="Inflation (%)",
    )

    st.info(
        "Interpretation: a visible relationship does not establish that "
        "COVID-19 or restrictions caused an economic outcome. Other "
        "factors, including supply disruptions, fiscal support, and "
        "country-specific conditions, may also matter."
    )

    # ---------------------------------------------------------
    # 5. Method and limitations
    # ---------------------------------------------------------
    st.divider()
    st.header("5. How to read the results")
    st.markdown(
        """
        - **Economic indicators:** annual observations from 2018 to 2024.
        - **Pandemic indicators:** monthly observations from 2020 to 2022.
        - **Comparison:** the same selected countries are used throughout.
        - **Baseline:** 2018–2019 provides a short pre-pandemic reference.
        - **Limitations:** only seven selected countries are included;
          reported health data may differ in quality; and correlation
          does not establish causation.
        """
    )

    st.caption(
        "The dashboard recalculates its displayed summaries when the "
        "country selection changes. Interpret findings in the context "
        "of the selected countries and available observations."
    )
