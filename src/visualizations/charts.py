
"""Plotly charts and shared chart styling for the COVID-19 dashboard.

`COUNTRY_COLORS`, `COUNTRY_SYMBOLS`, `COUNTRY_ORDER` and `style_figure()`
are used by every chart in `pages/home.py`, so each country keeps the same
colour, marker and legend position on every chart and for every filter
selection.
"""

import pandas as pd
import plotly.express as px
import streamlit as st


# Fixed order used for legends, tables, and colour assignment.
COUNTRY_ORDER = [
    "Brazil",
    "China",
    "France",
    "Germany",
    "India",
    "Rwanda",
    "United States",
]

# Colour-blind-safe Okabe-Ito hues (the same family as the EDA notebook).
# India and the United States are slightly darker than the original
# Okabe-Ito values so that every line has at least 3:1 contrast on white.
COUNTRY_COLORS = {
    "Brazil": "#009E73",         # bluish green
    "China": "#D55E00",          # vermillion
    "France": "#0072B2",         # blue
    "Germany": "#4D4D4D",        # dark grey
    "India": "#B87A00",          # dark orange
    "Rwanda": "#CC79A7",         # reddish purple
    "United States": "#2B8FCC",  # sky blue
}

# A different marker per country, so lines can be told apart without colour.
COUNTRY_SYMBOLS = {
    "Brazil": "circle",
    "China": "square",
    "France": "diamond",
    "Germany": "triangle-up",
    "India": "x",
    "Rwanda": "star",
    "United States": "cross",
}

# Shared look for reference lines (zero line, 2019 level, ...).
REFERENCE_LINE = dict(line_dash="dash", line_color="#6B7280", line_width=1)

# Keep the older name available for any code that imported it.
COLORS = [COUNTRY_COLORS[c] for c in COUNTRY_ORDER]


def country_style(markers: bool = True) -> dict:
    """Keyword arguments that give Plotly Express charts fixed country styling."""
    style = {
        "color_discrete_map": COUNTRY_COLORS,
        "category_orders": {"country": COUNTRY_ORDER},
    }
    if markers:
        style["symbol_map"] = COUNTRY_SYMBOLS
    return style


NAVY = "#1C2B44"
MUTED = "#5B6475"
GRID = "#EDE4DD"
FONT_FAMILY = "Inter, 'Source Sans Pro', Arial, sans-serif"


def style_figure(fig, height: int = 460, legend_title: str = "Country"):
    """Apply the dashboard's common layout: transparent background so the
    chart sits on its card, readable fonts, light grid lines."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, size=14, color=NAVY),
        title=dict(
            font=dict(size=17, color=NAVY),
            x=0, xanchor="left", y=0.97, yanchor="top",
        ),
        legend=dict(
            title_text=legend_title,
            font=dict(size=13),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=10, r=10, t=64, b=36),
        hoverlabel=dict(font_size=13, font_family=FONT_FAMILY),
    )
    fig.update_xaxes(
        showgrid=False, linecolor="#B9AEA6", ticks="outside",
        tickcolor="#B9AEA6", title_font=dict(color=MUTED),
    )
    fig.update_yaxes(
        gridcolor=GRID, zerolinecolor="#B9AEA6", title_font=dict(color=MUTED),
    )
    return fig


def _show_chart(fig, key: str) -> None:
    """Display a responsive Plotly chart in Streamlit."""
    style_figure(fig)
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, width="stretch", key=key)


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
        symbol="country",
        markers=True,
        title=title,
        labels={
            x: x.replace("_", " ").title(),
            y: y_label,
            "country": "Country",
        },
        **country_style(),
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
        title="COVID-19 Mortality and GDP Growth in 2020",
        labels={
            "new_deaths_per_million":
                "Sum of monthly deaths per million",
            economic_column: "GDP growth (%)",
        },
        **country_style(markers=False),
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

    plot_df[health_column] = pd.to_numeric(
        plot_df[health_column], errors="coerce"
    )
    plot_df[economic_column] = pd.to_numeric(
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
        **country_style(markers=False),
    )

    style_figure(fig, height=500)
    st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------------
# Builders used by the research pages
# ---------------------------------------------------------------------------

SHOCK_YEARS = (2020, 2021)


def shade_years(fig, start=SHOCK_YEARS[0], end=SHOCK_YEARS[1], label="2020–2021"):
    """Shade a block of years on an annual chart (default: the pandemic shock)."""
    fig.add_vrect(
        x0=start - 0.5,
        x1=end + 0.5,
        fillcolor="#F3E3E0",
        opacity=0.6,
        line_width=0,
        layer="below",
        annotation_text=label,
        annotation_position="top left",
        annotation_font_color=MUTED,
        annotation_font_size=12,
    )
    return fig


def country_line_chart(df, x, y, title, y_label, x_label=None, markers=True,
                       shade=False, zero_line=False, log_y=False):
    """Line chart with one line per country in the fixed colours."""
    plot_df = df.dropna(subset=[x, y]).sort_values(["country", x])
    if plot_df.empty:
        return None
    fig = px.line(
        plot_df,
        x=x,
        y=y,
        color="country",
        symbol="country" if markers else None,
        markers=markers,
        log_y=log_y,
        title=title,
        labels={
            x: x_label or ("Year" if x == "year" else "Month"),
            y: y_label,
            "country": "Country",
        },
        **country_style(markers=markers),
    )
    if x == "year":
        fig.update_xaxes(dtick=1)
    if shade:
        shade_years(fig)
    if zero_line:
        fig.add_hline(y=0, **REFERENCE_LINE)
    return fig


def country_bar_chart(df, value, title, value_label, text_format="+.1f",
                      unit="", zero_line=True):
    """Horizontal bars, one per country, sorted from lowest to highest."""
    plot_df = df.dropna(subset=[value]).sort_values(value)
    if plot_df.empty:
        return None
    fig = px.bar(
        plot_df,
        x=value,
        y="country",
        orientation="h",
        color="country",
        color_discrete_map=COUNTRY_COLORS,
        title=title,
        labels={value: value_label, "country": ""},
    )
    fig.update_traces(
        texttemplate=f"%{{x:{text_format}}}{unit}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=f"%{{y}}: %{{x:{text_format}}}{unit}<extra></extra>",
    )
    fig.update_yaxes(
        categoryorder="array", categoryarray=list(plot_df["country"])
    )
    fig.update_layout(showlegend=False, bargap=0.35)
    # Leave room beyond the longest bar so its value label is not clipped.
    low = min(0.0, float(plot_df[value].min()))
    high = max(0.0, float(plot_df[value].max()))
    pad = (high - low) * 0.2 or 1.0
    fig.update_xaxes(range=[low - pad if low < 0 else low, high + pad])
    if zero_line:
        fig.add_vline(x=0, line_color="#8C8079", line_width=1)
    return fig


def show_figure(fig, key, height=440, empty_message="No data for this selection."):
    """Style and display a chart inside a bordered card, or an info message."""
    with st.container(border=True):
        if fig is None:
            st.info(empty_message)
            return
        style_figure(fig, height=height)
        st.plotly_chart(fig, width="stretch", key=key)
