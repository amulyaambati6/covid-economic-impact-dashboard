"""Unit tests for the shared analysis functions in src/analysis/.

The expected values are the ones published in findings_summary.md, so the
dashboard pages (which all call these functions) agree with the document.
"""
import unittest

import pandas as pd

from src.analysis.correlation import correlation_tables, within_year_consistent
from src.analysis.economics import (
    country_summary_table,
    gdp_index_paths,
    recovery_table,
)
from tests.test_findings import economic_table, read

COUNTRIES = ["Brazil", "China", "France", "Germany", "India", "Rwanda", "United States"]


class EconomicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.econ = economic_table()
        cls.annual = read("merged_dataset_by_year.csv")

    def test_country_summary_table_matches_findings(self):
        table = country_summary_table(self.econ, self.annual, COUNTRIES).set_index("Country")
        expected = {
            # GDP 2020, unemployment change, inflation 2022, trend 2024, deaths, stringency
            "Rwanda": (-11.5, 0.6, 16.2, -11.1, 107, 53.8),
            "United States": (-4.9, 4.4, 5.9, -1.7, 3174, 48.4),
            "Germany": (-5.2, 0.7, 5.3, -5.1, 1971, 44.1),
            "India": (-10.9, 1.3, 2.9, -0.7, 372, 57.9),
            "Brazil": (-4.8, 1.8, 5.6, 3.4, 3296, 48.5),
            "France": (-9.3, -0.4, 3.7, -4.8, 2515, 42.3),
            "China": (-4.1, 0.4, -0.5, -7.1, 31, 73.3),
        }
        for country, values in expected.items():
            row = table.loc[country]
            with self.subTest(country=country):
                self.assertEqual(round(row.iloc[0], 1), values[0])
                self.assertEqual(round(row.iloc[1], 1), values[1])
                self.assertEqual(round(row.iloc[2], 1), values[2])
                self.assertEqual(round(row.iloc[3], 1), values[3])
                self.assertEqual(round(row.iloc[4]), values[4])
                self.assertEqual(round(row.iloc[5], 1), values[5])

    def test_gdp_index(self):
        index_df, final = gdp_index_paths(self.econ, COUNTRIES)
        actual = index_df[index_df["series"] == "Actual path"].set_index(["country", "year"])["index"]
        self.assertAlmostEqual(actual[("France", 2020)], 92.56, places=2)
        self.assertLess(actual[("France", 2021)], 100)
        self.assertLess(actual[("Germany", 2021)], 100)
        self.assertTrue((actual.xs(2022, level="year") > 100).all())
        self.assertEqual(int((final["Difference from trend (%)"] < 0).sum()), 6)

    def test_gdp_index_skips_incomplete_country(self):
        econ = self.econ[~((self.econ.country == "India") & (self.econ.year == 2022))]
        index_df, final = gdp_index_paths(econ, COUNTRIES)
        self.assertNotIn("India", set(index_df["country"]))
        self.assertEqual(len(final), 6)

    def test_unemployment_recovery_table(self):
        table = recovery_table(self.econ, "unemployment_pct", COUNTRIES).set_index("Country")
        back = table["Back to 2019 level by 2024?"]
        self.assertEqual(int((back == "Yes").sum()), 6)
        self.assertEqual(back["Rwanda"], "No")
        self.assertEqual(table.loc["Rwanda", "Peak year"], 2021)


class CorrelationTests(unittest.TestCase):
    def test_pooled_tests_and_correction(self):
        econ = economic_table()
        annual = read("merged_dataset_by_year.csv")
        pooled, within, years = correlation_tables(annual, econ)
        self.assertEqual(len(pooled), 9)
        self.assertEqual(int((pooled["p-value"] < 0.05).sum()), 1)
        self.assertEqual(int((pooled["Bonferroni-adjusted p"] < 0.05).sum()), 0)
        self.assertEqual(years, [2020, 2021, 2022])

        row = pooled[(pooled["Health or policy indicator"] == "Weighted stringency index")
                     & (pooled["Economic outcome"] == "Inflation difference (pp)")].iloc[0]
        self.assertAlmostEqual(row["Spearman rho"], -0.505, places=3)
        match = within.loc[row.name]
        self.assertFalse(within_year_consistent(match, row["Spearman rho"], years))

    def test_too_few_observations_returns_empty(self):
        econ = economic_table()
        annual = read("merged_dataset_by_year.csv")
        one = annual[annual["country"] == "China"].iloc[:2]
        pooled, _, _ = correlation_tables(one, econ)
        self.assertTrue(pooled.empty)


if __name__ == "__main__":
    unittest.main()
