
"""Plotly charts for the COVID-19 and global economy dashboard."""

import pandas as pd
import plotly.express as px
import streamlit as st


COLORS = px.colors.qualitative.Set2


def _show_chart(fig, key: str) -> None:
    """Display a responsive Plotly chart in Streamlit."""
    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        legend_title_text="Country",
        margin=dict(l=20, r=20, t=65, b=20),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _check_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    """Check that a dataset contains the columns a chart needs."""
    missing = [column for column in columns if column not in df.columns]

    if missing:
        st.warning(
            "This chart cannot be displayed. Missing columns: "
            + ", ".join(missing)
        )
        return False

    if df.empty:
        st.info("No data available for the current filters.")
        return False

    return True


def _country_line(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    y_label: str,
    key: str,
) -> None:
    """Create a consistent line chart grouped by country."""
    if not _check_columns(df, ["country", x, y]):
        return

    chart_df = df[["country", x, y]].copy()
    chart_df[y] = pd.to_numeric(chart_df[y], errors="coerce")
    chart_df = chart_df.dropna(subset=[x, y])

    if chart_df.empty:
        st.info("No valid observations are available for this chart.")
        return

    chart_df = chart_df.sort_values([ "country", x ])

    fig = px.line(
        chart_df,
        x=x,
        y=y,
        color="country",
        markers=True,
        color_discrete_sequence=COLORS,
        title=title,
        labels={
            x: x.replace("_", " ").title(),
            y: y_label,
            "country": "Country",
        },
    )
    _show_chart(fig, key)


def plot_gdp_growth(df: pd.DataFrame) -> None:
    """Research question: How did GDP growth change from 2018 to 2024?"""
    _country_line(
        df,
        x="year",
        y="gdp_growth_pct",
        title="Annual GDP Growth (2018–2024)",
        y_label="GDP growth (%)",
        key="gdp-growth-chart",
    )


def plot_inflation(df: pd.DataFrame) -> None:
    """Research question: How did inflation change during and after COVID-19?"""
    _country_line(
        df,
        x="year",
        y="inflation_pct",
        title="Annual Inflation (2018–2024)",
        y_label="Inflation (%)",
        key="inflation-chart",
    )


def plot_unemployment(df: pd.DataFrame) -> None:
    """Research question: How did unemployment change around 2020?"""
    _country_line(
        df,
        x="year",
        y="unemployment_pct",
        title="Annual Unemployment (2018–2024)",
        y_label="Unemployment (%)",
        key="unemployment-chart",
    )


def plot_covid_cases(df: pd.DataFrame) -> None:
    """Compare monthly reported new cases per million during 2020–2022."""
    if not _check_columns(
        df, ["country", "month", "new_cases_per_million"]
    ):
        return

    chart_df = df.copy()
    chart_df["month"] = pd.to_datetime(
        chart_df["month"], errors="coerce"
    )
    chart_df["new_cases_per_million"] = pd.to_numeric(
        chart_df["new_cases_per_million"], errors="coerce"
    )
    chart_df = chart_df[
        chart_df["month"].dt.year.between(2020, 2022)
    ].dropna(subset=["month", "new_cases_per_million"])

    _country_line(
        chart_df,
        x="month",
        y="new_cases_per_million",
        title="Monthly New COVID-19 Cases per Million (2020–2022)",
        y_label="New cases per million",
        key="covid-cases-chart",
    )


def plot_covid_deaths(df: pd.DataFrame) -> None:
    """Compare monthly reported new deaths per million during 2020–2022."""
    if not _check_columns(
        df, ["country", "month", "new_deaths_per_million"]
    ):
        return

    chart_df = df.copy()
    chart_df["month"] = pd.to_datetime(
        chart_df["month"], errors="coerce"
    )
    chart_df["new_deaths_per_million"] = pd.to_numeric(
        chart_df["new_deaths_per_million"], errors="coerce"
    )
    chart_df = chart_df[
        chart_df["month"].dt.year.between(2020, 2022)
    ].dropna(subset=["month", "new_deaths_per_million"])

    _country_line(
        chart_df,
        x="month",
        y="new_deaths_per_million",
        title="Monthly New COVID-19 Deaths per Million (2020–2022)",
        y_label="New deaths per million",
        key="covid-deaths-chart",
    )


def plot_stringency(df: pd.DataFrame) -> None:
    """Research question: How did government response stringency change?"""
    if not _check_columns(df, ["country", "month", "sti_weighted"]):
        return

    chart_df = df.copy()
    chart_df["month"] = pd.to_datetime(
        chart_df["month"], errors="coerce"
    )
    chart_df["sti_weighted"] = pd.to_numeric(
        chart_df["sti_weighted"], errors="coerce"
    )
    chart_df = chart_df[
        chart_df["month"].dt.year.between(2020, 2022)
    ].dropna(subset=["month", "sti_weighted"])

    _country_line(
        chart_df,
        x="month",
        y="sti_weighted",
        title="Government Response Stringency (2020–2022)",
        y_label="Stringency index (0–100)",
        key="stringency-chart",
    )


def plot_covid_economic_relationship(
    annual_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    economic_column: str = "gdp_growth_pct",
) -> None:
    """
    Compare 2020 GDP growth with total reported COVID-19 deaths
    per million across countries.

    This is an exploratory association, not a causal analysis.
    """
    required_annual = ["country", "year", economic_column]
    required_monthly = [
        "country",
        "month",
        "new_deaths_per_million",
    ]

    if not _check_columns(annual_df, required_annual):
        return

    if not _check_columns(monthly_df, required_monthly):
        return

    economic = annual_df.copy()
    economic["year"] = pd.to_numeric(economic["year"], errors="coerce")
    economic[economic_column] = pd.to_numeric(
        economic[economic_column], errors="coerce"
    )
    economic = economic[economic["year"] == 2020]
    economic = economic[["country", economic_column]].dropna()

    health = monthly_df.copy()
    health["month"] = pd.to_datetime(
        health["month"], errors="coerce"
    )
    health["new_deaths_per_million"] = pd.to_numeric(
        health["new_deaths_per_million"], errors="coerce"
    )
    health = health[health["month"].dt.year == 2020]

    # Sum observed monthly death rates for a descriptive annual total.
    # Missing months are excluded rather than filled with zero.
    mortality = (
        health.groupby("country", as_index=False)
        ["new_deaths_per_million"]
        .sum(min_count=1)
    )

    comparison = economic.merge(
        mortality, on="country", how="inner"
    ).dropna()

    if comparison.empty:
        st.info("No matching 2020 economic and mortality data.")
        return

    fig = px.scatter(
        comparison,
        x="new_deaths_per_million",
        y=economic_column,
        text="country",
        hover_name="country",
        color="country",
        color_discrete_sequence=COLORS,
        title="COVID-19 Mortality and GDP Growth in 2020",
        labels={
            "new_deaths_per_million":
                "Sum of monthly deaths per million",
            economic_column: "GDP growth (%)",
        },
    )
    fig.update_traces(textposition="top center")
    _show_chart(fig, "covid-economic-relationship-chart")

    st.caption(
        f"Countries compared: {len(comparison)}. "
        "This chart describes an association; it does not show that "
        "COVID-19 deaths caused a particular economic outcome."
    )


# Keep the older function name available if another file imports it.
def plot_economic_relationship(
    annual_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    economic_column: str = "gdp_growth_pct",
) -> None:
    plot_covid_economic_relationship(
        annual_df,
        monthly_df,
        economic_column=economic_column,
    )
    

def plot_health_economic_relationship(
    annual_df,
    health_column,
    economic_column,
    title,
    health_label,
    economic_label,
):
    """
    Compare one annual health/policy indicator with one
    annual economic indicator. Each point represents a country-year.
    """
    import plotly.express as px
    import streamlit as st

    required = {
        "country",
        "year",
        health_column,
        economic_column,
    }

    missing = required.difference(annual_df.columns)
    if missing:
        st.error(
            f"Cannot create '{title}'. Missing columns: "
            f"{', '.join(sorted(missing))}"
        )
        return

    plot_df = annual_df[
        ["country", "year", health_column, economic_column]
    ].copy()

    plot_df[health_column] = __import__("pandas").to_numeric(
        plot_df[health_column], errors="coerce"
    )
    plot_df[economic_column] = __import__("pandas").to_numeric(
        plot_df[economic_column], errors="coerce"
    )
    plot_df = plot_df.dropna(
        subset=[health_column, economic_column]
    )

    if plot_df.empty:
        st.warning(f"No complete data available for '{title}'.")
        return

    fig = px.scatter(
        plot_df,
        x=health_column,
        y=economic_column,
        color="country",
        hover_name="country",
        hover_data={"year": True},
        title=title,
        labels={
            health_column: health_label,
            economic_column: economic_label,
        },
    )

    fig.update_layout(
        legend_title_text="Country",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

