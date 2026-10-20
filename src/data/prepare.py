"""Load and combine the processed datasets once for every dashboard page."""

import pandas as pd
import streamlit as st

from src.analysis.economics import add_country_baselines
from src.data.loader import (
    load_annual_data,
    load_economic_data,
    load_monthly_data,
)
from src.visualizations.charts import COUNTRY_ORDER

ECONOMIC_COLUMNS = ["gdp_growth_pct", "inflation_pct", "unemployment_pct"]
PANDEMIC_YEARS = (2020, 2022)


def _prepare_year_column(df):
    """Convert year to integer and remove invalid years."""
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    return df


@st.cache_data
def load_dashboard_data():
    """Return a dict with the tables every page uses.

    economic: country-year economic indicators 2018-2024 plus each country's
              2018-2019 baseline and the differences from it (pp).
    monthly:  country-month cases, deaths and stringency, 2020-2022.
    annual:   country-year cases, deaths and stringency, 2020-2022.
    countries: countries present in both economic and monthly data,
               in the fixed dashboard order.
    """
    monthly = load_monthly_data().copy()
    annual = _prepare_year_column(load_annual_data())

    frames = []
    for column in ECONOMIC_COLUMNS:
        frame = _prepare_year_column(load_economic_data(column))
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        # Remove duplicate country-year rows before merging.
        frames.append(
            frame.drop_duplicates(["country", "year"])[["country", "year", column]]
        )

    economic = frames[0]
    for frame in frames[1:]:
        economic = economic.merge(
            frame, on=["country", "year"], how="outer", validate="one_to_one"
        )
    economic = add_country_baselines(economic)

    monthly["month"] = pd.to_datetime(monthly["month"].astype(str), errors="coerce")
    monthly = monthly.dropna(subset=["month"])
    monthly["year"] = monthly["month"].dt.year
    monthly = monthly[monthly["year"].between(*PANDEMIC_YEARS)]
    annual = annual[annual["year"].between(*PANDEMIC_YEARS)]

    available = set(economic["country"].dropna()) & set(monthly["country"].dropna())
    countries = [c for c in COUNTRY_ORDER if c in available]
    countries += sorted(available - set(countries))

    return {
        "economic": economic,
        "monthly": monthly,
        "annual": annual,
        "countries": countries,
    }
