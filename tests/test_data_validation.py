"""Basic checks for missing-year detection."""
import unittest

from src.data.validation import missing_years


class MissingYearsTests(unittest.TestCase):
    def test_reports_missing_years_in_order(self):
        self.assertEqual(missing_years(range(2019, 2024), [2020, 2022]), [2019, 2021, 2023])

    def test_no_missing_years(self):
        self.assertEqual(missing_years([2019, 2020], [2020, 2019]), [])


if __name__ == "__main__":
    unittest.main()
