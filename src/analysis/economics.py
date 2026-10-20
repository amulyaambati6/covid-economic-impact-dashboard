"""Economic calculations shared by every dashboard page.

All functions are plain pandas (no Streamlit), so they can be tested
directly and give the same numbers on every page.
"""

import numpy as np
import pandas as pd

BASELINE_YEARS = (2018, 2019)
RECOVERY_YEARS = list(range(2020, 2025))


def add_country_baselines(economic):
    """Calculate 2018-2019 baselines and percentage-point differences."""
    baseline = (
        economic[economic["year"].isin(BASELINE_YEARS)]
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
    for indicator in ["gdp", "inflation", "unemployment"]:
        year_count = f"{indicator}_baseline_years"
        baseline_col = f"{indicator}_baseline"
        economic.loc[economic[year_count] < 2, baseline_col] = np.nan

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


def value_change(econ, column, start_year, end_year):
    """Each country's change in `column` from start_year to end_year."""
    pivot = econ[econ["year"].isin([start_year, end_year])].pivot_table(
        index="country", columns="year", values=column, aggfunc="first"
    )
    if not {start_year, end_year}.issubset(pivot.columns):
        return pd.Series(dtype=float)
    return (pivot[end_year] - pivot[start_year]).dropna()


def unemployment_change_2019_2020(econ):
    """Each country's unemployment change from 2019 to 2020 (pp)."""
    return value_change(econ, "unemployment_pct", 2019, 2020)


def gdp_index_paths(econ, countries):
    """Reconstruct a GDP index (2019 = 100) and a pre-COVID trend benchmark.

    The actual index compounds each year's real GDP growth. The benchmark
    compounds the country's average 2018-2019 growth. A country is skipped
    unless both baseline years and every year 2020-2024 are available, so no
    path is drawn across missing years.

    Returns (index_rows, final_rows) as DataFrames.
    """
    index_rows = []
    final_rows = []

    for country in countries:
        country_data = econ[econ["country"] == country].sort_values("year")
        if country_data["year"].duplicated().any():
            continue

        growth = country_data.set_index("year")["gdp_growth_pct"]
        baseline = growth.reindex(BASELINE_YEARS)
        if baseline.isna().any():
            continue
        if growth.reindex(RECOVERY_YEARS).isna().any():
            continue

        baseline_growth = baseline.mean()
        actual_index = trend_index = 100.0
        index_rows.append((country, 2019, "Actual path", 100.0))
        index_rows.append((country, 2019, "Pre-COVID trend benchmark", 100.0))

        for year in RECOVERY_YEARS:
            actual_index *= 1 + growth[year] / 100
            trend_index *= 1 + baseline_growth / 100
            index_rows.append((country, year, "Actual path", actual_index))
            index_rows.append(
                (country, year, "Pre-COVID trend benchmark", trend_index)
            )

        final_rows.append({
            "Country": country,
            "Actual GDP index (2024)": actual_index,
            "Trend benchmark (2024)": trend_index,
            "Difference from trend (%)": (actual_index / trend_index - 1) * 100,
        })

    index_df = pd.DataFrame(
        index_rows, columns=["country", "year", "series", "index"]
    )
    final_df = pd.DataFrame(final_rows)
    return index_df, final_df


def recovery_table(econ, column, countries):
    """2019 value, peak 2020-24 (and its year), and 2024 value per country.

    For unemployment it also says whether the rate was back at or below its
    2019 value in any year from 2021 to 2024.
    """
    rows = []
    for country in countries:
        series = (
            econ[econ["country"] == country]
            .set_index("year")[column]
            .dropna()
        )
        if series.empty:
            continue
        after = series.loc[2020:2024]
        row = {
            "Country": country,
            "2019": series.get(2019, np.nan),
            "Peak 2020–24": after.max() if not after.empty else np.nan,
            "Peak year": int(after.idxmax()) if not after.empty else None,
            "2024": series.get(2024, np.nan),
        }
        if column == "unemployment_pct":
            later = series.loc[2021:2024]
            if 2019 in series.index and not later.empty:
                row["Back to 2019 level by 2024?"] = (
                    "Yes" if (later <= series[2019]).any() else "No"
                )
            else:
                row["Back to 2019 level by 2024?"] = "—"
        rows.append(row)
    return pd.DataFrame(rows)


def country_summary_table(econ, annual, countries):
    """One row per country with the headline impact measures.

    Every measure compares the country with its own 2018-2019 normal, so
    countries with different typical growth or inflation are comparable.
    """
    _, final = gdp_index_paths(econ, countries)
    trend_gap = (
        final.set_index("Country")["Difference from trend (%)"]
        if not final.empty else pd.Series(dtype=float)
    )
    unemployment = unemployment_change_2019_2020(econ)
    by_year = econ.set_index(["country", "year"])
    health = annual[annual["country"].isin(countries)].groupby("country")

    rows = []
    for country in countries:
        def effect(column, year):
            key = (country, year)
            return by_year[column].get(key, np.nan) if key in by_year.index else np.nan

        rows.append({
            "Country": country,
            "GDP vs own normal, 2020 (pp)": effect("gdp_effect_pp", 2020),
            "Unemployment change 2019–20 (pp)": unemployment.get(country, np.nan),
            "Inflation vs own normal, 2022 (pp)": effect("inflation_effect_pp", 2022),
            "Economy vs trend, 2024 (%)": trend_gap.get(country, np.nan),
            "Reported deaths per million, 2020–22": (
                health["new_deaths_per_million"].sum(min_count=1).get(country, np.nan)
            ),
            "Average stringency, 2020–22": (
                health["sti_weighted"].mean().get(country, np.nan)
            ),
        })
    return pd.DataFrame(rows)
