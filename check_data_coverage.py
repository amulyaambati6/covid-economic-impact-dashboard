"""Audit World Bank indicator coverage for the candidate study countries.

Run with: python check_data_coverage.py
Requires internet access when run. Writes a small coverage CSV, not source datasets.
"""
import csv
import json
import urllib.error
import urllib.request
from pathlib import Path

COUNTRIES = {
    "USA": "United States", "IND": "India", "FRA": "France", "CHN": "China",
    "BRA": "Brazil", "DEU": "Germany", "RWA": "Rwanda",
}
INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
}
YEARS = range(2019, 2024)
OUTPUT = Path("data/processed/coverage_audit.csv")


def fetch_values(country_code: str, indicator_code: str) -> dict[int, float | None]:
    """Fetch annual values from the World Bank API for one country/indicator."""
    url = (
        f"https://api.worldbank.org/v2/country/{country_code}/indicator/"
        f"{indicator_code}?date=2019:2023&format=json&per_page=100"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "CentraleDigitalLab-student-project/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return {}
    return {
        int(item["date"]): item["value"]
        for item in payload[1]
        if item.get("date") and int(item["date"]) in YEARS
    }


def audit_coverage() -> list[dict[str, object]]:
    """Build one audit row for each country, indicator, and expected year."""
    rows = []
    for country_code, country_name in COUNTRIES.items():
        for indicator_code, indicator_name in INDICATORS.items():
            try:
                values = fetch_values(country_code, indicator_code)
                error = ""
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
                values = {}
                error = f"Request or response error: {exc}"
            for year in YEARS:
                value = values.get(year)
                rows.append({
                    "country_code": country_code,
                    "country": country_name,
                    "indicator_code": indicator_code,
                    "indicator": indicator_name,
                    "year": year,
                    "available": value is not None,
                    "value": value,
                    "note": error if error else ("Missing value in source" if value is None else ""),
                })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    results = audit_coverage()
    missing = sum(not row["available"] for row in results)
    print(f"Coverage audit saved to {OUTPUT} ({len(results)} country/indicator/year rows).")
    print(f"Missing or unverified values: {missing} of {len(results)}.")
    print("Review the note column: API errors are recorded as unverified, not as proven gaps.")
