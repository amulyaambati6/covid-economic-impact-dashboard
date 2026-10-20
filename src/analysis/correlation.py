"""Exploratory Spearman correlations between pandemic and economic measures.

Each observation is a country-year (2020-2022). The functions return the
pooled correlations with a Bonferroni correction, plus the same correlation
inside each single year, so the dashboard can show when a pooled result is
really a difference between years.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HEALTH_MEASURES = [
    ("new_deaths_per_million", "Reported deaths per million"),
    ("new_cases_per_million", "Reported cases per million"),
    ("sti_weighted", "Weighted stringency index"),
]

ECONOMIC_EFFECTS = [
    ("gdp_effect_pp", "GDP growth difference (pp)"),
    ("unemployment_effect_pp", "Unemployment difference (pp)"),
    ("inflation_effect_pp", "Inflation difference (pp)"),
]


def spearman_or_nan(x, y):
    """Spearman rho, p-value and n, or NaN when the data cannot support one."""
    pair = pd.concat([x, y], axis=1).dropna()
    if (
        len(pair) < 3
        or pair.iloc[:, 0].nunique() < 2
        or pair.iloc[:, 1].nunique() < 2
    ):
        return np.nan, np.nan, len(pair)
    rho, p_value = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
    return float(rho), float(p_value), len(pair)


def correlation_tables(annual, econ):
    """Return (pooled, within_year, years).

    pooled: one row per pair with rho, p-value and Bonferroni-adjusted p.
    within_year: the same pairs with rho computed inside each single year.
    """
    health = [(c, label) for c, label in HEALTH_MEASURES if c in annual.columns]
    data = annual[["country", "year"] + [c for c, _ in health]].merge(
        econ[["country", "year"] + [c for c, _ in ECONOMIC_EFFECTS]],
        on=["country", "year"],
        how="inner",
        validate="one_to_one",
    )
    years = sorted(data["year"].unique())

    pooled_rows, within_rows = [], []
    for x_col, x_label in health:
        for y_col, y_label in ECONOMIC_EFFECTS:
            rho, p_value, n_obs = spearman_or_nan(data[x_col], data[y_col])
            # Skip pairs without enough complete, varying observations.
            if np.isnan(rho):
                continue
            pooled_rows.append({
                "Health or policy indicator": x_label,
                "Economic outcome": y_label,
                "Observations": n_obs,
                "Spearman rho": rho,
                "p-value": p_value,
            })
            within = {
                "Health or policy indicator": x_label,
                "Economic outcome": y_label,
                "Pooled rho": rho,
            }
            for year in years:
                one_year = data[data["year"] == year]
                within[str(year)] = spearman_or_nan(
                    one_year[x_col], one_year[y_col]
                )[0]
            within_rows.append(within)

    pooled = pd.DataFrame(pooled_rows)
    if not pooled.empty:
        # Bonferroni: multiply each p-value by the number of tests run.
        pooled["Bonferroni-adjusted p"] = (
            pooled["p-value"] * len(pooled)
        ).clip(upper=1)
    return pooled, pd.DataFrame(within_rows), years


def within_year_consistent(within_row, pooled_rho, years):
    """True if every single-year rho has the same sign as the pooled rho."""
    signs = {
        np.sign(within_row[str(y)]) for y in years
        if pd.notna(within_row[str(y)])
    }
    return signs == {np.sign(pooled_rho)}
