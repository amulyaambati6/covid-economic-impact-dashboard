"""Integrity checks for the processed datasets the dashboard reads.

The expected values below describe the committed data in data/processed/.
If a teammate re-runs the pipeline with new source data, a failing test is
a prompt to review the change, not necessarily a bug.
"""
import unittest
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

COUNTRIES = {
    "Brazil", "China", "France", "Germany", "India", "Rwanda", "United States",
}
CODES = {"BRA", "CHN", "FRA", "DEU", "IND", "RWA", "USA"}
ECONOMIC_YEARS = set(range(2018, 2025))
PANDEMIC_YEARS = {2020, 2021, 2022}
PANDEMIC_MONTHS = {
    f"{year}-{month:02d}" for year in PANDEMIC_YEARS for month in range(1, 13)
}

ECONOMIC_FILES = {
    "gdp_growth_pct": "gdp_growth_pct_annual.csv",
    "inflation_pct": "inflation_pct_annual.csv",
    "unemployment_pct": "unemployment_pct_annual.csv",
}
MONTHLY_VALUES = [
    "new_cases_per_million", "new_deaths_per_million",
    "sti_vaccinated", "sti_nonvaccinated", "sti_weighted",
]


def read(name):
    """Read a processed CSV whatever its separator (, or ;)."""
    return pd.read_csv(PROCESSED / name, sep=None, engine="python")


class EconomicFileTests(unittest.TestCase):
    def test_each_indicator_file(self):
        for column, name in ECONOMIC_FILES.items():
            with self.subTest(file=name):
                df = read(name)
                self.assertEqual(
                    set(df.columns), {"country", "code", "year", column}
                )
                self.assertEqual(set(df["country"]), COUNTRIES)
                self.assertEqual(set(df["code"]), CODES)
                self.assertEqual(set(df["year"]), ECONOMIC_YEARS)
                self.assertFalse(df.duplicated(["code", "year"]).any())
                self.assertEqual(len(df), 7 * 7)
                self.assertTrue(pd.api.types.is_numeric_dtype(df[column]))
                # The current World Bank download has no gaps 2018-2024.
                self.assertEqual(int(df[column].isna().sum()), 0)

    def test_country_names_match_codes_everywhere(self):
        pairs = None
        for name in list(ECONOMIC_FILES.values()) + [
            "merged_dataset_by_month.csv", "merged_dataset_by_year.csv",
        ]:
            these = set(map(tuple, read(name)[["country", "code"]].values))
            pairs = pairs or these
            self.assertEqual(these, pairs, name)


class MergedFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monthly = read("merged_dataset_by_month.csv")
        cls.yearly = read("merged_dataset_by_year.csv")

    def test_monthly_coverage_and_keys(self):
        m = self.monthly
        self.assertEqual(set(m["country"]), COUNTRIES)
        self.assertEqual(set(m["month"]), PANDEMIC_MONTHS)
        self.assertEqual(len(m), 7 * 36)
        self.assertFalse(m.duplicated(["code", "month"]).any())
        self.assertEqual(int(m.isna().sum().sum()), 0)

    def test_yearly_coverage_and_keys(self):
        y = self.yearly
        self.assertEqual(set(y["country"]), COUNTRIES)
        self.assertEqual(set(y["year"]), PANDEMIC_YEARS)
        self.assertEqual(len(y), 7 * 3)
        self.assertFalse(y.duplicated(["code", "year"]).any())
        self.assertEqual(int(y.isna().sum().sum()), 0)

    def test_value_ranges(self):
        m = self.monthly
        for column in ["sti_vaccinated", "sti_nonvaccinated", "sti_weighted"]:
            self.assertTrue(m[column].between(0, 100).all(), column)
        for column in ["new_cases_per_million", "new_deaths_per_million"]:
            self.assertTrue((m[column] >= 0).all(), column)

    def test_yearly_totals_equal_monthly_sums(self):
        m = self.monthly.assign(year=self.monthly["month"].str[:4].astype(int))
        sums = m.groupby(["code", "year"])[
            ["new_cases_per_million", "new_deaths_per_million"]
        ].sum()
        y = self.yearly.set_index(["code", "year"])[sums.columns]
        pd.testing.assert_frame_equal(
            sums.loc[y.index].round(2), y.round(2), check_exact=False,
            atol=0.01,
        )

    def test_yearly_stringency_is_mean_of_months(self):
        m = self.monthly.assign(year=self.monthly["month"].str[:4].astype(int))
        means = m.groupby(["code", "year"])["sti_weighted"].mean()
        y = self.yearly.set_index(["code", "year"])["sti_weighted"]
        self.assertLess((means.loc[y.index] - y).abs().max(), 0.01)

    def test_economic_columns_match_annual_files(self):
        y = self.yearly
        for column, name in ECONOMIC_FILES.items():
            annual = read(name).set_index(["code", "year"])[column]
            merged = y.set_index(["code", "year"])[column]
            self.assertLess((annual.loc[merged.index] - merged).abs().max(), 1e-9)


if __name__ == "__main__":
    unittest.main()
