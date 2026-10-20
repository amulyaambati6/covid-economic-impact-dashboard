"""Check headline numbers in findings_summary.md against the processed data.

Each test recomputes a figure quoted in findings_summary.md with the same
method the dashboard uses, so the document and the app cannot silently
drift apart.
"""
import unittest
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

from src.analysis.economics import add_country_baselines

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"


def read(name):
    return pd.read_csv(PROCESSED / name, sep=None, engine="python")


def economic_table():
    gdp = read("gdp_growth_pct_annual.csv")
    inflation = read("inflation_pct_annual.csv")
    unemployment = read("unemployment_pct_annual.csv")
    economic = gdp.merge(inflation, on=["country", "code", "year"]).merge(
        unemployment, on=["country", "code", "year"]
    )
    return add_country_baselines(economic)


class EconomicFindingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eco = economic_table()
        cls.by_year = cls.eco.groupby("year")

    def value(self, country, year, column):
        row = self.eco[(self.eco.country == country) & (self.eco.year == year)]
        return float(row[column].iloc[0])

    def test_median_gdp_growth(self):
        medians = self.by_year["gdp_growth_pct"].median().round(1)
        self.assertEqual(medians[2019], 2.6)
        self.assertEqual(medians[2020], -3.3)
        self.assertEqual(medians[2021], 6.9)

    def test_six_of_seven_contracted_in_2020(self):
        growth_2020 = self.eco[self.eco.year == 2020].set_index("country")[
            "gdp_growth_pct"
        ]
        self.assertEqual(int((growth_2020 < 0).sum()), 6)
        self.assertGreater(growth_2020["China"], 0)

    def test_gdp_shortfalls_against_own_baseline(self):
        effects = self.eco[self.eco.year == 2020].set_index("country")[
            "gdp_effect_pp"
        ].sort_values()
        self.assertEqual(list(effects.index[:3]), ["Rwanda", "India", "France"])
        self.assertEqual(
            [round(v, 1) for v in effects.iloc[:3]], [-11.5, -10.9, -9.3]
        )

    def test_unemployment_rise_united_states(self):
        rise = self.value("United States", 2020, "unemployment_pct") - self.value(
            "United States", 2019, "unemployment_pct"
        )
        self.assertEqual(round(rise, 1), 4.4)

    def test_median_inflation(self):
        medians = self.by_year["inflation_pct"].median().round(1)
        self.assertEqual(medians[2020], 2.4)
        self.assertEqual(medians[2022], 6.9)

    def test_rwanda_inflation_effect_2022(self):
        self.assertEqual(round(self.value("Rwanda", 2022, "inflation_effect_pp"), 1), 16.2)


class PandemicFindingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yearly = read("merged_dataset_by_year.csv")

    def test_total_reported_deaths(self):
        totals = self.yearly.groupby("country")["new_deaths_per_million"].sum()
        self.assertEqual(round(totals["Brazil"]), 3296)
        self.assertEqual(round(totals["United States"]), 3174)
        self.assertEqual(round(totals["China"]), 31)

    def test_stringency_inflation_correlation_is_a_year_effect(self):
        """Pooled rho is negative, but it is positive within 2020."""
        eco = economic_table()
        data = self.yearly[["country", "year", "sti_weighted"]].merge(
            eco[["country", "year", "inflation_effect_pp"]],
            on=["country", "year"],
        )
        pooled, p_value = spearmanr(data.sti_weighted, data.inflation_effect_pp)
        self.assertAlmostEqual(pooled, -0.51, places=2)
        self.assertGreater(p_value * 9, 0.05)  # not significant after Bonferroni
        within_2020 = data[data.year == 2020]
        rho_2020, _ = spearmanr(
            within_2020.sti_weighted, within_2020.inflation_effect_pp
        )
        self.assertGreater(rho_2020, 0)

    def test_deaths_vs_gdp_2020(self):
        eco = economic_table()
        data = self.yearly[self.yearly.year == 2020].merge(
            eco[["country", "year", "gdp_effect_pp"]], on=["country", "year"]
        )
        rho, _ = spearmanr(data.new_deaths_per_million, data.gdp_effect_pp)
        self.assertEqual(round(rho, 2), 0.07)


if __name__ == "__main__":
    unittest.main()
