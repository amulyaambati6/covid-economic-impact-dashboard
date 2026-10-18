
"""Load processed datasets for the COVID-19 dashboard."""

from pathlib import Path

import pandas as pd
import streamlit as st


# Project root: the folder containing app.py and data/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"


@st.cache_data
def load_monthly_data() -> pd.DataFrame:
    """Load the merged monthly dataset for 2020–2022."""
    file_path = PROCESSED_DATA / "merged_dataset_by_month.csv"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Monthly dataset not found: {file_path}"
        )

    df = pd.read_csv(file_path, sep=None, engine="python")

    if "month" not in df.columns:
        raise ValueError(
            "The monthly dataset must contain a 'month' column. "
            "Check the CSV delimiter and column names."
        )

    df["month"] = pd.to_datetime(
        df["month"].astype(str),
        errors="coerce",
    )

    df = df.dropna(subset=["month"])

    # Keep the project's pandemic analysis period.
    df = df[df["month"].dt.year.between(2020, 2022)].copy()

    return df


@st.cache_data
def load_annual_data() -> pd.DataFrame:
    """Load the merged annual dataset for 2020–2022."""
    file_path = PROCESSED_DATA / "merged_dataset_by_year.csv"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Annual dataset not found: {file_path}"
        )

    df = pd.read_csv(file_path, sep=None, engine="python")

    if "year" not in df.columns:
        raise ValueError(
            "The annual dataset must contain a 'year' column. "
            "Check the CSV delimiter and column names."
        )

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    return df


@st.cache_data
def load_economic_data(indicator: str) -> pd.DataFrame:
    """
    Load a separate annual economic dataset.

    Supported indicators: gdp_growth_pct, inflation_pct,
    unemployment_pct.
    """
    allowed_indicators = {
        "gdp_growth_pct",
        "inflation_pct",
        "unemployment_pct",
    }

    if indicator not in allowed_indicators:
        raise ValueError(
            f"Unsupported indicator: {indicator}"
        )

    file_path = PROCESSED_DATA / f"{indicator.replace('_pct', '_pct')}_annual.csv"

    # Use the actual filenames in data/processed.
    filename_map = {
        "gdp_growth_pct": "gdp_growth_pct_annual.csv",
        "inflation_pct": "inflation_pct_annual.csv",
        "unemployment_pct": "unemployment_pct_annual.csv",
    }

    file_path = PROCESSED_DATA / filename_map[indicator]

    if not file_path.exists():
        raise FileNotFoundError(
            f"Economic dataset not found: {file_path}"
        )

    df = pd.read_csv(file_path, sep=None, engine="python")

    required_columns = {"country", "year", indicator}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"{file_path.name} is missing columns: "
            f"{', '.join(sorted(missing_columns))}. "
            "Check the CSV delimiter and column names."
        )

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df[indicator] = pd.to_numeric(df[indicator], errors="coerce")

    df = df.dropna(subset=["country", "year", indicator]).copy()
    df["year"] = df["year"].astype(int)

    # Keep the available historical period; do not invent missing years.
    return df.sort_values(["country", "year"]).reset_index(drop=True)
