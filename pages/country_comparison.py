"""Research page 5: Country Comparisons."""

import plotly.express as px
import streamlit as st

from src.analysis.correlation import spearman_or_nan
from src.analysis.economics import country_summary_table
from src.visualizations.charts import (
    REFERENCE_LINE,
    country_bar_chart,
    country_style,
    show_figure,
)
from src.visualizations.layout import (
    html_block,
    load_data_or_stop,
    notes_card,
    page_header,
    require_countries,
    section_title,
    sidebar_filters,
)

# label: (table, column, unit, number format, note)
INDICATORS = {
    "GDP growth (%)": ("economic", "gdp_growth_pct", "%", "+.1f",
                       "Annual real GDP growth."),
    "GDP growth vs own 2018–19 average (pp)": (
        "economic", "gdp_effect_pp", " pp", "+.1f",
        "Growth minus the country's 2018–2019 average."),
    "Unemployment rate (%)": ("economic", "unemployment_pct", "%", ".1f",
                              "Share of the labour force (modelled ILO estimate)."),
    "Unemployment vs own 2018–19 average (pp)": (
        "economic", "unemployment_effect_pp", " pp", "+.1f",
        "Unemployment minus the country's 2018–2019 average."),
    "Inflation (%)": ("economic", "inflation_pct", "%", "+.1f",
                      "Annual consumer price inflation."),
    "Inflation vs own 2018–19 average (pp)": (
        "economic", "inflation_effect_pp", " pp", "+.1f",
        "Inflation minus the country's 2018–2019 average."),
    "Reported COVID-19 deaths per million (year total)": (
        "annual", "new_deaths_per_million", "", ",.0f",
        "Sum of the reported monthly figures for the year."),
    "Reported COVID-19 cases per million (year total)": (
        "annual", "new_cases_per_million", "", ",.0f",
        "Sum of the reported monthly figures; depends on testing."),
    "Average stringency index (0–100)": (
        "annual", "sti_weighted", "", ".1f",
        "Mean of the monthly stringency index for the year."),
}


def render_country_comparison(data, countries, years):
    econ = data["economic"][data["economic"]["country"].isin(countries)]
    ann = data["annual"][data["annual"]["country"].isin(countries)]

    page_header(
        "comparison",
        "Rank the selected countries on any indicator and year, see the headline "
        "impact measures side by side, and check whether the 2020 economic loss "
        "followed the reported death toll.",
    )

    c1, c2 = st.columns([2, 1])
    label = c1.selectbox("Indicator", list(INDICATORS), key="compare_indicator")
    table_name, column, unit, number_format, note = INDICATORS[label]
    source = econ if table_name == "economic" else ann
    available_years = sorted(source.dropna(subset=[column])["year"].unique())
    default_year = 2020 if 2020 in available_years else available_years[-1]
    year = c2.selectbox(
        "Year", available_years, index=available_years.index(default_year),
        key=f"compare_year_{table_name}",
        help="This page has its own year selector; the sidebar year range "
        "does not apply here.",
    )

    values = source[source["year"] == year][["country", column]]
    fig = country_bar_chart(
        values, column, f"{label}, {year}", label, text_format=number_format,
        unit=unit, zero_line=not column.startswith(("new_", "sti", "unemployment_pct")),
    )
    show_figure(fig, "compare-bar", height=400)
    st.caption(f"{note} Countries are sorted from lowest to highest.")

    section_title(
        "Headline impact measures",
        "Each economic measure compares the country with its own 2018–2019 normal or trend.",
    )
    summary = country_summary_table(econ, ann, countries).rename(columns={
        "GDP vs own normal, 2020 (pp)": "GDP vs normal 2020 (pp)",
        "Unemployment change 2019–20 (pp)": "Unemployment Δ 2019–20 (pp)",
        "Inflation vs own normal, 2022 (pp)": "Inflation vs normal 2022 (pp)",
        "Economy vs trend, 2024 (%)": "GDP vs trend 2024 (%)",
        "Reported deaths per million, 2020–22": "Deaths per million 2020–22",
        "Average stringency, 2020–22": "Avg stringency 2020–22",
    })
    with st.container(border=True):
        st.dataframe(
            summary.style.format({
                "GDP vs normal 2020 (pp)": "{:+.1f}",
                "Unemployment Δ 2019–20 (pp)": "{:+.1f}",
                "Inflation vs normal 2022 (pp)": "{:+.1f}",
                "GDP vs trend 2024 (%)": "{:+.1f}",
                "Deaths per million 2020–22": "{:,.0f}",
                "Avg stringency 2020–22": "{:.1f}",
            }, na_rep="—"),
            hide_index=True, width="stretch",
        )
        st.caption(
            "'Normal' = the country's own 2018–2019 average. 'Trend' = 2018–2019 "
            "average growth continued from 2019. Deaths are reported figures."
        )
        st.caption(
            "No single 'most affected' ranking is shown: combining measures in "
            "different units needs a weighting choice the data cannot justify."
        )

    section_title(
        "Did the 2020 economic loss follow the reported death toll?",
        "One point per country. The horizontal axis is logarithmic because reported "
        "deaths differ more than a hundredfold.",
    )
    deaths = ann[ann["year"] == 2020][["country", "new_deaths_per_million"]]
    loss = econ[econ["year"] == 2020][["country", "gdp_effect_pp"]]
    points = deaths.merge(loss, on="country").dropna()
    points = points[points["new_deaths_per_million"] > 0]
    if points.empty:
        show_figure(None, "compare-scatter")
    else:
        fig = px.scatter(
            points, x="new_deaths_per_million", y="gdp_effect_pp", color="country",
            symbol="country", text="country", log_x=True,
            title="2020: reported deaths vs GDP growth against own normal",
            labels={
                "new_deaths_per_million": "Reported deaths per million, 2020 (log scale)",
                "gdp_effect_pp": "GDP growth minus 2018–19 average (pp)",
                "country": "Country",
            },
            **country_style(),
        )
        fig.update_traces(marker=dict(size=15, line=dict(width=1.5, color="white")),
                          textposition="top center")
        # Brazil and the United States sit almost on top of each other.
        label_side = {"Brazil": "bottom left", "United States": "top right",
                      "Germany": "top left"}
        fig.for_each_trace(
            lambda t: t.update(textposition=label_side.get(t.name, "top center"))
        )
        fig.add_hline(y=0, **REFERENCE_LINE)
        fig.update_layout(showlegend=False)
        show_figure(fig, "compare-scatter", height=460)
        rho, p_value, n_obs = spearman_or_nan(
            points["new_deaths_per_million"], points["gdp_effect_pp"]
        )
        if rho == rho:  # not NaN
            html_block(
                f'<p class="inline-insight">Rank correlation between 2020 reported deaths '
                f"and the GDP shortfall: <b>ρ = {rho:+.2f}</b> (n = {n_obs}, p = {p_value:.2f}). "
                + ("There is no clear rank pattern between reported deaths and the "
                   "economic loss." if abs(rho) < 0.3 else
                   "With so few countries this is exploratory, not evidence of cause.")
                + "</p>"
            )

    notes_card([
        "Comparisons against each country's own normal remove differences in typical "
        "growth or inflation, but two baseline years (2018–2019) are a short normal.",
        "Reported deaths depend on testing and registration rules, which differ "
        "between countries.",
        "Seven countries are a small, purposive sample, not a representative picture "
        "of the world economy.",
    ])


def show_country_comparison():
    data = load_data_or_stop()
    countries, years = sidebar_filters(data["countries"], show_years=False)
    require_countries(countries)
    render_country_comparison(data, countries, years)
