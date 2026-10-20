"""Checks for the MySQL bonus files that do not need a MySQL server.

The full database check (loading into MySQL and comparing the views with
data/processed/) is database/verify_database.py, run by hand.
"""
import re
import unittest
from pathlib import Path

from database.build_load_script import INDICATORS, build_sql, collect_rows

DATABASE = Path(__file__).resolve().parents[1] / "database"


class LoadScriptTests(unittest.TestCase):
    def test_load_data_sql_is_up_to_date(self):
        """load_data.sql must match the current processed CSV files."""
        expected, _ = build_sql()
        actual = (DATABASE / "load_data.sql").read_text(encoding="utf-8")
        self.assertEqual(actual, expected,
                         "Run: python database/build_load_script.py")

    def test_row_counts(self):
        rows = collect_rows()
        self.assertEqual(len(rows["country"]), 7)
        self.assertEqual(len(rows["indicator"]), 8)
        # 3 indicators x 7 countries x 7 years (2018-2024), none missing.
        self.assertEqual(len(rows["annual_observation"]), 147)
        # 486 x 2 cases/deaths values minus 43 missing, plus 252 x 3 stringency.
        self.assertEqual(len(rows["monthly_observation"]), 486 * 2 - 43 + 252 * 3)

    def test_keys_are_unique_and_valid(self):
        rows = collect_rows()
        countries = {code for code, _ in rows["country"]}
        indicators = {row[0] for row in INDICATORS}
        for table in ["annual_observation", "monthly_observation"]:
            keys = [row[:3] for row in rows[table]]
            self.assertEqual(len(keys), len(set(keys)), f"duplicate key in {table}")
            self.assertTrue({k[0] for k in keys} <= countries)
            self.assertTrue({k[1] for k in keys} <= indicators)
        self.assertTrue(all(row[2].endswith("-01") for row in rows["monthly_observation"]))

    def test_schema_defines_every_table_and_view(self):
        schema = (DATABASE / "schema.sql").read_text(encoding="utf-8")
        tables = set(re.findall(r"CREATE TABLE (\w+)", schema))
        views = set(re.findall(r"CREATE VIEW (\w+)", schema))
        self.assertEqual(tables, {"data_source", "country", "indicator",
                                  "annual_observation", "monthly_observation"})
        self.assertEqual(views, {"v_economic_annual", "v_economic_baseline",
                                 "v_economic_vs_baseline", "v_pandemic_yearly",
                                 "v_merged_by_year"})


if __name__ == "__main__":
    unittest.main()
