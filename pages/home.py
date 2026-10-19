
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from scipy.stats import spearmanr

from src.data.loader import (
    load_monthly_data,
    load_annual_data,
    load_economic_data,
)


COUNTRY_ORDER = [
    "Brazil",
    "China",
    "France",
    "Germany",
    "India",
    "Rwanda",
    "United States",
]


# =============================================================
# HELPERS
# =============================================================

def prepare_year_column(df):
    """Convert year to integer and remove invalid years."""
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    return df


def add_country_baselines(economic):
    """Calculate 2018-2019 baselines and percentage-point differences."""
    baseline = (
        economic[economic["year"].isin([2018, 2019])]
        .groupby("country", as_index=False)
        .agg(
            gdp_baseline=("gdp_growth_pct", "mean"),
            inflation_baseline=("inflation_pct", "mean"),
            unemployment_baseline=("unemployment_pct", "mean"),
            gdp_baseline_years=("gdp_growth_pct", "count"),
            inflation_baseline_years=("inflation_pct", "count"),
            unemployment_baseline_years=("unemployment_pct", "count"),
        )
    )

    economic = economic.merge(baseline, on="country", how="left")

    # Require both baseline years for a reliable comparison.
    for indicator in [
        "gdp",
        "inflation",
        "unemployment",
    ]:
        year_count = f"{indicator}_baseline_years"
        baseline_col = f"{indicator}_baseline"

        economic.loc[
            economic[year_count] < 2, baseline_col
        ] = np.nan

    economic["gdp_effect_pp"] = (
        economic["gdp_growth_pct"] - economic["gdp_baseline"]
    )
    economic["inflation_effect_pp"] = (
        economic["inflation_pct"] - economic["inflation_baseline"]
    )
    economic["unemployment_effect_pp"] = (
        economic["unemployment_pct"] - economic["unemployment_baseline"]
    )

    return economic


def make_line_chart(
    df,
    x,
    y,
    title,
    y_label,
    color="country",
):
    """Build a consistent line chart if usable data exist."""
    if df.empty or y not in df.columns:
        st.info(f"No data available for: {title}.")
        return

    plot_df = df.dropna(subset=[x, y]).copy()

    if plot_df.empty:
        st.info(f"No valid observations available for: {title}.")
        return

    fig = px.line(
        plot_df,
        x=x,
        y=y,
        color=color,
        markers=True,
        title=title,
        labels={
            x: "Year" if x == "year" else "Month",
            y: y_label,
            "country": "Country",
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def format_pp(value):
    """Format a percentage-point difference."""
    return "N/A" if pd.isna(value) else f"{value:+.1f} pp"


# =============================================================
# MAIN DASHBOARD
# =============================================================

def show_home():
    st.title("📊 Dashboard & Analysis")

    st.markdown(
        """
        Explore how the COVID-19 pandemic coincided with changes in
        economic growth, unemployment, inflation, reported cases,
        reported deaths, and policy stringency.

        **Main question:** How did the economic impact differ across
        the seven selected countries, and were those differences
        associated with pandemic severity or policy stringency?
        """
    )

    # ---------------------------------------------------------
    # 1. LOAD DATA
    # ---------------------------------------------------------

    try:
        monthly = load_monthly_data().copy()
        annual_health = load_annual_data().copy()
        gdp = load_economic_data("gdp_growth_pct").copy()
        inflation = load_economic_data("inflation_pct").copy()
        unemployment = load_economic_data("unemployment_pct").copy()

    except Exception as exc:
        st.error(f"Could not load the project datasets: {exc}")
        st.info(
            "Check the processed CSV files and src/data/loader.py."
        )
        return

    required_columns = {
        "country",
        "month",
        "new_cases_per_million",
        "new_deaths_per_million",
    }

    missing = required_columns - set(monthly.columns)
    if missing:
        st.error(
            "The monthly dataset is missing these columns: "
            + ", ".join(sorted(missing))
        )
        return

    for frame_name, frame, value_col in [
        ("GDP", gdp, "gdp_growth_pct"),
        ("Inflation", inflation, "inflation_pct"),
        ("Unemployment", unemployment, "unemployment_pct"),
    ]:
        needed = {"country", "year", value_col}
        missing = needed - set(frame.columns)
        if missing:
            st.error(
                f"The {frame_name} dataset is missing: "
                + ", ".join(sorted(missing))
            )
            return

    monthly["month"] = pd.to_datetime(
        monthly["month"].astype(str),
        errors="coerce",
    )
    monthly = monthly.dropna(subset=["month"])
    monthly["year"] = monthly["month"].dt.year
    monthly = monthly[monthly["year"].between(2020, 2022)]

    annual_health = prepare_year_column(annual_health)
    annual_health = annual_health[
        annual_health["year"].between(2020, 2022)
    ]

    gdp = prepare_year_column(gdp)
    inflation = prepare_year_column(inflation)
    unemployment = prepare_year_column(unemployment)

    for frame, value_col in [
        (gdp, "gdp_growth_pct"),
        (inflation, "inflation_pct"),
        (unemployment, "unemployment_pct"),
    ]:
        frame[value_col] = pd.to_numeric(
            frame[value_col], errors="coerce"
        )

    # Remove duplicate country-year rows before merging.
    gdp = gdp.drop_duplicates(["country", "year"])
    inflation = inflation.drop_duplicates(["country", "year"])
    unemployment = unemployment.drop_duplicates(["country", "year"])

    economic = (
        gdp[["country", "year", "gdp_growth_pct"]]
        .merge(
            inflation[["country", "year", "inflation_pct"]],
            on=["country", "year"],
            how="outer",
            validate="one_to_one",
        )
        .merge(
            unemployment[["country", "year", "unemployment_pct"]],
            on=["country", "year"],
            how="outer",
            validate="one_to_one",
        )
    )

    economic = add_country_baselines(economic)

    # Keep countries available in both economic and monthly data.
    available = (
        set(economic["country"].dropna())
        & set(monthly["country"].dropna())
    )
    countries = [c for c in COUNTRY_ORDER if c in available]
    countries += sorted(available - set(countries))

    if not countries:
        st.error("No matching countries were found across the datasets.")
        return

    # ---------------------------------------------------------
    # 2. FILTERS
    # ---------------------------------------------------------

    st.sidebar.header("Dashboard filters")

    selected_countries = st.sidebar.multiselect(
        "Select countries",
        options=countries,
        default=countries,
    )

    if not selected_countries:
        st.warning("Select at least one country to view the analysis.")
        return

    econ = economic[
        economic["country"].isin(selected_countries)
    ].copy()

    mon = monthly[
        monthly["country"].isin(selected_countries)
    ].copy()

    ann = annual_health[
        annual_health["country"].isin(selected_countries)
    ].copy()

    st.sidebar.caption(
        "Charts, summary statistics, and findings update with your selection."
    )

    # ---------------------------------------------------------
    # 3. EXECUTIVE SUMMARY
    # ---------------------------------------------------------

    st.header("At a glance")

    gdp_2020 = econ.loc[
        econ["year"] == 2020,
        ["country", "gdp_growth_pct"],
    ].dropna()

    unemployment_pivot = econ[
        econ["year"].isin([2019, 2020])
    ].pivot_table(
        index="country",
        columns="year",
        values="unemployment_pct",
        aggfunc="first",
    )

    if {2019, 2020}.issubset(unemployment_pivot.columns):
        unemployment_change = (
            unemployment_pivot[2020] - unemployment_pivot[2019]
        ).dropna()
    else:
        unemployment_change = pd.Series(dtype=float)

    inflation_2022 = econ.loc[
        econ["year"] == 2022,
        ["country", "inflation_pct"],
    ].dropna()

    c1, c2, c3 = st.columns(3)

    with c1:
        if not gdp_2020.empty:
            median_growth = gdp_2020["gdp_growth_pct"].median()
            contractions = int(
                (gdp_2020["gdp_growth_pct"] < 0).sum()
            )
            st.metric("Median GDP growth · 2020", f"{median_growth:.1f}%")
            st.caption(
                f"{contractions} of {len(gdp_2020)} countries "
                "had negative GDP growth."
            )
        else:
            st.metric("Median GDP growth · 2020", "N/A")

    with c2:
        if not unemployment_change.empty:
            worst_country = unemployment_change.idxmax()
            worst_change = unemployment_change.max()
            st.metric("Largest unemployment rise · 2019–2020",
                      f"{worst_change:+.1f} pp")
            st.caption(f"Country: {worst_country}")
        else:
            st.metric("Unemployment rise · 2019–2020", "N/A")

    with c3:
        if not inflation_2022.empty:
            st.metric(
                "Median inflation · 2022",
                f"{inflation_2022['inflation_pct'].median():.1f}%",
            )
            st.caption(
                f"Across {len(inflation_2022)} selected countries."
            )
        else:
            st.metric("Median inflation · 2022", "N/A")

    st.caption(
        "pp = percentage points. Median values describe the selected "
        "countries, not the entire world economy."
    )

    # ---------------------------------------------------------
    # 4. GDP GROWTH
    # ---------------------------------------------------------

    st.header("1. Economic growth")

    st.markdown(
        """
        **Research question:** How did GDP growth change during the
        pandemic, and how did the experience differ across countries?
        """
    )

    gdp_period = st.selectbox(
        "GDP chart period",
        ["2018–2024", "2018–2022", "2020–2022"],
        key="gdp_period",
    )

    period_map = {
        "2018–2024": (2018, 2024),
        "2018–2022": (2018, 2022),
        "2020–2022": (2020, 2022),
    }
    start_year, end_year = period_map[gdp_period]
    gdp_plot = econ[econ["year"].between(start_year, end_year)]

    if not gdp_plot["gdp_growth_pct"].dropna().empty:
        fig = px.line(
            gdp_plot.dropna(subset=["gdp_growth_pct"]),
            x="year",
            y="gdp_growth_pct",
            color="country",
            markers=True,
            title="Annual GDP growth by country",
            labels={
                "year": "Year",
                "gdp_growth_pct": "GDP growth (%)",
                "country": "Country",
            },
        )
        fig.add_hline(y=0, line_dash="dash")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No GDP growth data are available for this period.")

    gdp_effect = econ[
        (econ["year"] == 2020)
        & econ["gdp_effect_pp"].notna()
    ]

    if not gdp_effect.empty:
        worst = gdp_effect.loc[gdp_effect["gdp_effect_pp"].idxmin()]
        st.info(
            f"In 2020, **{worst['country']}** had the largest decline "
            f"relative to its 2018–2019 average GDP growth "
            f"({worst['gdp_effect_pp']:.1f} percentage points)."
        )

    st.caption(
        "GDP growth is the annual rate of change in GDP. The difference "
        "from a country's 2018–2019 average is in percentage points; "
        "it is not the percentage change in GDP level."
    )

    # ---------------------------------------------------------
    # 5. UNEMPLOYMENT
    # ---------------------------------------------------------

    st.header("2. Employment and unemployment")

    st.markdown(
        """
        **Research question:** Which countries saw the largest
        unemployment changes, and how did unemployment evolve afterwards?
        """
    )

    unemployment_plot = econ.dropna(subset=["unemployment_pct"])

    make_line_chart(
        unemployment_plot,
        "year",
        "unemployment_pct",
        "Annual unemployment rate",
        "Unemployment rate (%)",
    )

    unemp_2020 = econ[
        (econ["year"] == 2020)
        & econ["unemployment_effect_pp"].notna()
    ]

    if not unemp_2020.empty:
        largest = unemp_2020.loc[
            unemp_2020["unemployment_effect_pp"].idxmax()
        ]
        st.info(
            f"Relative to its 2018–2019 average, **{largest['country']}** "
            f"had the largest unemployment increase in 2020 "
            f"({largest['unemployment_effect_pp']:+.1f} pp)."
        )

    # ---------------------------------------------------------
    # 6. INFLATION
    # ---------------------------------------------------------

    st.header("3. Inflation")

    st.markdown(
        """
        **Research question:** How did inflation evolve during the
        pandemic and the following years?
        """
    )

    inflation_plot = econ.dropna(subset=["inflation_pct"])

    make_line_chart(
        inflation_plot,
        "year",
        "inflation_pct",
        "Annual inflation rate",
        "Inflation rate (%)",
    )

    inflation_2022_effect = econ[
        (econ["year"] == 2022)
        & econ["inflation_effect_pp"].notna()
    ]

    if not inflation_2022_effect.empty:
        largest = inflation_2022_effect.loc[
            inflation_2022_effect["inflation_effect_pp"].idxmax()
        ]
        st.info(
            f"In 2022, **{largest['country']}** had the largest inflation "
            f"difference from its 2018–2019 average "
            f"({largest['inflation_effect_pp']:+.1f} pp)."
        )

    # ---------------------------------------------------------
    # 7. COVID-19 CASES AND DEATHS
    # ---------------------------------------------------------

    st.header("4. Pandemic severity")

    st.markdown(
        """
        **Research question:** How did reported COVID-19 cases and deaths
        change from month to month?
        """
    )

    health_options = {
        "New cases per million": "new_cases_per_million",
        "New deaths per million": "new_deaths_per_million",
    }

    health_choice = st.radio(
        "Choose a health indicator",
        list(health_options.keys()),
        horizontal=True,
    )
    health_column = health_options[health_choice]

    if health_column in mon.columns:
        health_plot = mon.dropna(subset=[health_column])

        if not health_plot.empty:
            fig = px.line(
                health_plot,
                x="month",
                y=health_column,
                color="country",
                title=f"Monthly {health_choice.lower()}",
                labels={
                    "month": "Month",
                    health_column: "Per million people",
                    "country": "Country",
                },
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid observations are available for this indicator.")
    else:
        st.warning(f"The dataset does not contain {health_column}.")

    st.caption(
        "These are monthly reported rates. Summing monthly values is not "
        "a substitute for a separately validated cumulative mortality "
        "measure. Differences in testing and reporting affect comparisons."
    )

    # ---------------------------------------------------------
    # 8. POLICY STRINGENCY
    # ---------------------------------------------------------

    st.header("5. Policy stringency")

    st.markdown(
        """
        **Research question:** How did restrictions change between 2020
        and 2022, and how much did the two stringency measures differ?
        """
    )

    if "sti_weighted" in mon.columns:
        policy_plot = mon.dropna(subset=["sti_weighted"])

        make_line_chart(
            policy_plot,
            "month",
            "sti_weighted",
            "Monthly weighted policy stringency index",
            "Stringency index",
        )
    else:
        st.warning("The monthly data do not contain sti_weighted.")

    required_gap_cols = {"sti_vaccinated", "sti_nonvaccinated"}

    if required_gap_cols.issubset(mon.columns):
        gap = mon.copy()
        gap["stringency_gap"] = (
            gap["sti_nonvaccinated"] - gap["sti_vaccinated"]
        )
        gap = gap.dropna(subset=["stringency_gap"])

        if not gap.empty:
            fig = px.line(
                gap,
                x="month",
                y="stringency_gap",
                color="country",
                title="Stringency difference: non-vaccinated minus vaccinated",
                labels={
                    "month": "Month",
                    "stringency_gap": "Index-point difference",
                    "country": "Country",
                },
            )
            fig.add_hline(y=0, line_dash="dash")
            st.plotly_chart(fig, use_container_width=True)

            st.caption(
                "Positive values mean the non-vaccinated stringency "
                "measure is higher; negative values mean it is lower."
            )

    st.caption(
        "The stringency index describes policy measures. It does not "
        "directly measure compliance, policy effectiveness, or economic damage."
    )

    # ---------------------------------------------------------
    # 9. CORRELATIONS
    # ---------------------------------------------------------

    st.header("6. Relationships between the pandemic and the economy")

    st.markdown(
        """
        **Research question:** Were pandemic severity or policy stringency
        associated with economic changes?

        Spearman correlation measures whether two variables tend to move
        together in rank. The results are exploratory and do not establish
        that one variable caused another.
        """
    )

    health_columns = [
        ("new_deaths_per_million", "Reported deaths per million"),
        ("new_cases_per_million", "Reported cases per million"),
        ("sti_weighted", "Weighted stringency index"),
    ]

    effect_columns = [
        ("gdp_effect_pp", "GDP growth difference (pp)"),
        ("unemployment_effect_pp", "Unemployment difference (pp)"),
        ("inflation_effect_pp", "Inflation difference (pp)"),
    ]

    available_health = [
        (column, label)
        for column, label in health_columns
        if column in ann.columns
    ]

    if available_health and not ann.empty:
        health_cols = [column for column, _ in available_health]

        correlation_data = ann[
            ["country", "year"] + health_cols
        ].copy()

        effect_data = econ[
            ["country", "year"]
            + [column for column, _ in effect_columns]
        ].copy()

        correlation_data = correlation_data.merge(
            effect_data,
            on=["country", "year"],
            how="inner",
            validate="one_to_one",
        )

        rows = []

        for x_col, x_label in available_health:
            for y_col, y_label in effect_columns:
                pair = correlation_data[[x_col, y_col]].dropna()

                # Require at least three observations and variation
                # in both variables before calculating Spearman rho.
                if (
                    len(pair) < 3
                    or pair[x_col].nunique() < 2
                    or pair[y_col].nunique() < 2
                ):
                    continue

                rho, p_value = spearmanr(
                    pair[x_col],
                    pair[y_col],
                )

                rows.append({
                    "Health or policy indicator": x_label,
                    "Economic outcome": y_label,
                    "Observations": len(pair),
                    "Spearman rho": rho,
                    "p-value": p_value,
                })

        if rows:
            corr_df = pd.DataFrame(rows)

            st.dataframe(
                corr_df.style.format({
                    "Spearman rho": "{:.2f}",
                    "p-value": "{:.3f}",
                }),
                use_container_width=True,
                hide_index=True,
            )

            # Display the strongest absolute observed association,
            # without describing it as a causal relationship.
            valid_corr = corr_df.dropna(subset=["Spearman rho"])

            if not valid_corr.empty:
                strongest = valid_corr.loc[
                    valid_corr["Spearman rho"].abs().idxmax()
                ]
                st.write(
                    f"**Strongest observed rank association:** "
                    f"{strongest['Health or policy indicator']} and "
                    f"{strongest['Economic outcome']} "
                    f"(Spearman ρ = {strongest['Spearman rho']:.2f}, "
                    f"n = {int(strongest['Observations'])})."
                )

            st.caption(
                "The observations are country-years, not independent "
                "random samples. Countries repeat across years, the sample "
                "is small, and multiple tests raise the risk of false "
                "positives. Interpret p-values cautiously; correlation "
                "does not establish causation."
            )
        else:
            st.warning(
                "There are not enough complete, varying observations "
                "to calculate the correlations."
            )
    else:
        st.warning(
            "Health and policy variables needed for correlation analysis "
            "are not available."
        )

    # ---------------------------------------------------------
    # 10. COUNTRY COMPARISON TABLE
    # ---------------------------------------------------------

    st.header("7. Country comparison")

    st.write(
        "Compare annual economic indicators with each country's "
        "2018–2019 average."
    )

    score_year = st.selectbox(
        "Choose a year",
        options=list(range(2018, 2025)),
        index=2,
        key="score_year",
    )

    score = econ[econ["year"] == score_year].copy()

    display_columns = [
        "country",
        "year",
        "gdp_growth_pct",
        "gdp_effect_pp",
        "unemployment_pct",
        "unemployment_effect_pp",
        "inflation_pct",
        "inflation_effect_pp",
    ]

    display_columns = [
        column for column in display_columns
        if column in score.columns
    ]

    if not score.empty:
        st.dataframe(
            score[display_columns]
            .sort_values("country")
            .style.format(
                {
                    "gdp_growth_pct": "{:.2f}%",
                    "gdp_effect_pp": "{:+.2f} pp",
                    "unemployment_pct": "{:.2f}%",
                    "unemployment_effect_pp": "{:+.2f} pp",
                    "inflation_pct": "{:.2f}%",
                    "inflation_effect_pp": "{:+.2f} pp",
                },
                na_rep="—",
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning(f"No economic observations are available for {score_year}.")

    # ---------------------------------------------------------
    # 11. ECONOMIC RECOVERY
    # ---------------------------------------------------------

    show_recovery_analysis(selected_countries)

    # ---------------------------------------------------------
    # 12. CONCLUSIONS AND LIMITATIONS
    # ---------------------------------------------------------

    st.header("What can we conclude?")

    st.markdown(
        """
        - **Economic growth:** GDP growth reveals the immediate contraction
          and subsequent growth patterns, but positive growth alone does
          not prove that an economy has regained its previous trajectory.
        - **Employment:** Changes in unemployment differed across
          countries and should be compared with each country's baseline.
        - **Inflation:** Inflation followed a different trajectory from
          GDP growth and unemployment; a lower inflation rate does not
          necessarily mean prices have fallen.
        - **Pandemic and policy:** Cases, deaths, and stringency provide
          context for economic changes, but descriptive comparisons and
          correlations cannot identify causal effects.
        """
    )

    st.subheader("Limitations")

    st.markdown(
        """
        - The analysis covers seven selected countries, not the entire world.
        - COVID-19 and policy indicators are restricted to 2020–2022.
        - The pre-pandemic comparison uses only 2018 and 2019.
        - Reported cases and deaths may not be fully comparable between countries.
        - The GDP trend benchmark is illustrative, not a causal forecast.
        - Country-year correlation samples are small and observations
          from the same country may not be independent.
        """
    )

    st.caption(
        "Source: the project's processed datasets. Economic differences "
        "are calculated as the annual indicator minus the country's "
        "2018–2019 average. GDP growth differences and rate differences "
        "are expressed in percentage points."
    )


# =============================================================
# ECONOMIC RECOVERY ANALYSIS
# =============================================================

def show_recovery_analysis(selected_countries):
    """Compare GDP recovery with an illustrative pre-COVID benchmark."""

    st.header("8. Economic recovery: 2018–2024")

    st.markdown(
        """
        **Research question:** By 2024, how did reconstructed GDP levels
        compare with a benchmark based on each country's 2018–2019 average
        annual GDP growth?
        """
    )

    try:
        gdp = load_economic_data("gdp_growth_pct").copy()
        unemployment = load_economic_data("unemployment_pct").copy()
        inflation = load_economic_data("inflation_pct").copy()
    except Exception as exc:
        st.error(f"Could not load recovery datasets: {exc}")
        return

    gdp = prepare_year_column(gdp)
    unemployment = prepare_year_column(unemployment)
    inflation = prepare_year_column(inflation)

    for frame, value_col in [
        (gdp, "gdp_growth_pct"),
        (unemployment, "unemployment_pct"),
        (inflation, "inflation_pct"),
    ]:
        frame[value_col] = pd.to_numeric(
            frame[value_col], errors="coerce"
        )

    gdp = gdp.drop_duplicates(["country", "year"])
    unemployment = unemployment.drop_duplicates(["country", "year"])
    inflation = inflation.drop_duplicates(["country", "year"])

    gdp = gdp[gdp["country"].isin(selected_countries)].copy()
    unemployment = unemployment[
        unemployment["country"].isin(selected_countries)
    ].copy()
    inflation = inflation[
        inflation["country"].isin(selected_countries)
    ].copy()

    # ---------------------------------------------------------
    # A. RECONSTRUCTED GDP INDEX
    # ---------------------------------------------------------

    st.subheader("A. GDP index: 2019 = 100")

    st.caption(
        "The benchmark assumes that each country's average 2018–2019 "
        "annual GDP growth would have continued after 2019. This is a "
        "simplified comparison, not an estimate of what would have "
        "happened without the pandemic."
    )

    index_rows = []
    final_rows = []

    for country in selected_countries:
        country_data = (
            gdp[gdp["country"] == country]
            .sort_values("year")
            .copy()
        )

        # Require valid values for both baseline years.
        baseline_rows = country_data[
            country_data["year"].isin([2018, 2019])
        ].dropna(subset=["gdp_growth_pct"])

        if (
            baseline_rows["year"].nunique() < 2
            or country_data["year"].duplicated().any()
        ):
            continue

        baseline_growth = baseline_rows["gdp_growth_pct"].mean()

        annual_growth = (
            country_data.set_index("year")["gdp_growth_pct"]
        )

        # Do not draw a misleading recovery path across missing years.
        required_years = list(range(2020, 2025))

        if not all(
            year in annual_growth.index
            and pd.notna(annual_growth.loc[year])
            for year in required_years
        ):
            continue

        actual_index = 100.0
        trend_index = 100.0

        index_rows.extend([
            {
                "country": country,
                "year": 2019,
                "series": "Actual path",
                "index": 100.0,
            },
            {
                "country": country,
                "year": 2019,
                "series": "Pre-COVID trend benchmark",
                "index": 100.0,
            },
        ])

        for year in required_years:
            actual_index *= (
                1 + annual_growth.loc[year] / 100
            )
            trend_index *= (
                1 + baseline_growth / 100
            )

            index_rows.extend([
                {
                    "country": country,
                    "year": year,
                    "series": "Actual path",
                    "index": actual_index,
                },
                {
                    "country": country,
                    "year": year,
                    "series": "Pre-COVID trend benchmark",
                    "index": trend_index,
                },
            ])

        difference_pct = (
            (actual_index / trend_index) - 1
        ) * 100 if trend_index != 0 else np.nan

        final_rows.append({
            "Country": country,
            "Actual GDP index (2024)": actual_index,
            "Trend benchmark (2024)": trend_index,
            "Difference from trend (%)": difference_pct,
        })

    index_df = pd.DataFrame(index_rows)

    if not index_df.empty:
        fig = px.line(
            index_df,
            x="year",
            y="index",
            color="country",
            line_dash="series",
            markers=True,
            title="Reconstructed GDP index vs pre-COVID benchmark",
            labels={
                "year": "Year",
                "index": "GDP index (2019 = 100)",
                "country": "Country",
                "series": "Measure",
            },
        )

        fig.add_hline(
            y=100,
            line_dash="dot",
            annotation_text="2019 level",
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "The index is reconstructed by compounding annual GDP growth "
            "rates. It is not a directly observed GDP-level series."
        )
    else:
        st.warning(
            "The GDP recovery chart requires valid 2018 and 2019 baseline "
            "growth and complete, non-missing annual growth rates for "
            "every year from 2020 through 2024."
        )

    # ---------------------------------------------------------
    # B. DISTANCE FROM THE BENCHMARK IN 2024
    # ---------------------------------------------------------

    st.subheader("B. Difference from the benchmark in 2024")

    comparison = pd.DataFrame(final_rows)

    if not comparison.empty:
        comparison = comparison.sort_values(
            "Difference from trend (%)"
        )

        fig = px.bar(
            comparison,
            x="Country",
            y="Difference from trend (%)",
            title="2024 reconstructed GDP index relative to benchmark",
            labels={
                "Difference from trend (%)": "Difference from benchmark (%)"
            },
        )
        fig.add_hline(y=0, line_dash="dash")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            comparison.style.format({
                "Actual GDP index (2024)": "{:.2f}",
                "Trend benchmark (2024)": "{:.2f}",
                "Difference from trend (%)": "{:+.2f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )

        worst = comparison.iloc[0]
        best = comparison.iloc[-1]

        st.write(
            f"**Largest shortfall from the benchmark:** "
            f"{worst['Country']} ({worst['Difference from trend (%)']:+.2f}%)."
        )
        st.write(
            f"**Highest relative position:** {best['Country']} "
            f"({best['Difference from trend (%)']:+.2f}%)."
        )

        st.caption(
            "These are differences from a hypothetical benchmark, not "
            "estimates of GDP lost because of COVID-19."
        )
    else:
        st.info(
            "No countries have the complete data required for the 2024 comparison."
        )

    # ---------------------------------------------------------
    # C. UNEMPLOYMENT RECOVERY
    # ---------------------------------------------------------

    st.subheader("C. Unemployment after 2019")

    if not unemployment.empty:
        make_line_chart(
            unemployment,
            "year",
            "unemployment_pct",
            "Unemployment rate, 2018–2024",
            "Unemployment rate (%)",
        )
    else:
        st.info("No unemployment data are available for the selected countries.")

    # ---------------------------------------------------------
    # D. INFLATION
    # ---------------------------------------------------------

    st.subheader("D. Inflation after 2019")

    if not inflation.empty:
        make_line_chart(
            inflation,
            "year",
            "inflation_pct",
            "Inflation rate, 2018–2024",
            "Inflation rate (%)",
        )
    else:
        st.info("No inflation data are available for the selected countries.")

    st.info(
        "Recovery has several dimensions: GDP growth measures the pace "
        "of economic change, the reconstructed index compares estimated "
        "GDP levels, unemployment measures labour-market conditions, "
        "and inflation measures the rate at which prices rise. These "
        "indicators should not be treated as interchangeable."
    )


# =============================================================
# RUN DIRECTLY ONLY WHEN THIS FILE IS EXECUTED AS A SCRIPT
# Streamlit app navigation should import and call show_home().
# =============================================================

if __name__ == "__main__":
    show_home()
