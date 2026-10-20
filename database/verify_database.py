"""Check that the MySQL database matches the processed CSV files.

Runs queries through the `mysql` command-line client and compares the
results with data/processed/, the files the dashboard reads. It also
checks that the constraints reject invalid data.

Run from the project root after loading schema.sql and load_data.sql:
    python database/verify_database.py --user root --password
`--password` makes the mysql client ask for the password on the terminal,
so it is never stored in a file or in this script. Use --host and --port
for a server that is not on localhost:3306, and --mysql to give the path
to mysql.exe if it is not on PATH.
"""

import argparse
import io
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DEFAULT_MYSQL = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="3306")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", action="store_true",
                        help="ask for the password (mysql -p)")
    parser.add_argument("--mysql", default=shutil.which("mysql") or DEFAULT_MYSQL,
                        help="path to the mysql client")
    return parser.parse_args()


class Database:
    def __init__(self, args):
        self.base = [args.mysql, "-h", args.host, "-P", str(args.port), "-u", args.user,
                     "--batch", "--default-character-set=utf8mb4", "covid_economy"]
        if args.password:
            self.base.insert(-1, "-p")

    def query(self, sql):
        """Run a SELECT and return a DataFrame."""
        result = subprocess.run(self.base + ["-e", sql], capture_output=True, text=True,
                                encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return pd.read_csv(io.StringIO(result.stdout), sep="\t", na_values=["NULL"])

    def must_fail(self, sql):
        """Run a statement that should be rejected; return the error text."""
        result = subprocess.run(self.base + ["-e", f"START TRANSACTION; {sql} ROLLBACK;"],
                                capture_output=True, text=True, encoding="utf-8")
        return result.returncode != 0, result.stderr.strip().splitlines()[-1:]


def read_processed(name):
    if name == "stringency_monthly.csv":
        return pd.read_csv(PROCESSED / name, sep=";", decimal=",", encoding="utf-8-sig")
    return pd.read_csv(PROCESSED / name, sep=None, engine="python", encoding="utf-8-sig")


def compare(label, db, csv, keys, tolerance):
    """True if both tables have the same keys and values within tolerance."""
    db = db.sort_values(keys).reset_index(drop=True)
    csv = csv.sort_values(keys).reset_index(drop=True)
    if db[keys].astype(str).values.tolist() != csv[keys].astype(str).values.tolist():
        print(f"FAIL  {label}: different rows ({len(db)} in MySQL, {len(csv)} in CSV)")
        return False
    columns = [c for c in csv.columns if c not in keys and c in db.columns
               and pd.api.types.is_numeric_dtype(csv[c])]
    worst = max((db[c].astype(float) - csv[c].astype(float)).abs().max() for c in columns)
    ok = worst <= tolerance + 1e-9  # allow for float noise at the tolerance itself
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {len(db)} rows, largest difference {worst:.4f}")
    return ok


def main():
    args = parse_args()
    db = Database(args)
    results = []

    # 1. Annual economic data equal the processed annual files.
    annual = db.query("SELECT country, code, year, gdp_growth_pct, inflation_pct, "
                      "unemployment_pct FROM v_economic_annual")
    csv = read_processed("gdp_growth_pct_annual.csv")
    for name in ["inflation_pct_annual.csv", "unemployment_pct_annual.csv"]:
        csv = csv.merge(read_processed(name), on=["country", "code", "year"])
    results.append(compare("v_economic_annual = *_annual.csv", annual, csv,
                           ["code", "year"], 0.0005))

    # 2. The yearly view rebuilds merged_dataset_by_year.csv. Up to 0.01 apart:
    #    MySQL rounds exact decimals (France 2022 stringency 19.905 -> 19.91),
    #    pandas rounded binary floats (19.90499... -> 19.90).
    merged = db.query("SELECT * FROM v_merged_by_year")
    results.append(compare("v_merged_by_year = merged_dataset_by_year.csv", merged,
                           read_processed("merged_dataset_by_year.csv"),
                           ["code", "year"], 0.01))

    # 3. Monthly values equal the processed monthly files (missing values absent).
    monthly = db.query(
        "SELECT m.country_code AS code, DATE_FORMAT(m.month_start, '%Y-%m') AS month, "
        "i.column_name AS indicator, m.value FROM monthly_observation m "
        "JOIN indicator i USING (indicator_code)")
    long_csv = pd.concat([
        read_processed(name).melt(id_vars=["country", "code", "month"],
                                  var_name="indicator", value_name="value").dropna()
        for name in ["cases_deaths_monthly.csv", "stringency_monthly.csv"]
    ]).drop(columns="country")
    results.append(compare("monthly_observation = monthly CSV files", monthly, long_csv,
                           ["code", "month", "indicator"], 0.0005))

    # 4. Baseline view gives the dashboard's headline figure.
    rwanda = db.query("SELECT difference_pp FROM v_economic_vs_baseline "
                      "WHERE code = 'RWA' AND indicator = 'gdp_growth_pct' AND year = 2020")
    value = float(rwanda["difference_pp"].iloc[0])
    ok = round(value, 1) == -11.5
    print(f"{'PASS' if ok else 'FAIL'}  Rwanda 2020 GDP vs own 2018-2019 average = {value:.2f} pp (expected -11.5)")
    results.append(ok)

    # 5. Constraints reject invalid data.
    checks = {
        "unknown country (foreign key)":
            "INSERT INTO annual_observation VALUES ('XXX', 'NY.GDP.MKTP.KD.ZG', 2020, 1);",
        "duplicate country-indicator-year (primary key)":
            "INSERT INTO annual_observation VALUES ('FRA', 'NY.GDP.MKTP.KD.ZG', 2020, 1);",
        "month not starting on day 1 (check)":
            "INSERT INTO monthly_observation VALUES ('FRA', 'OXCGRT.STI_WEIGHTED', '2023-01-15', 1);",
        "annual indicator with yearly aggregation (check)":
            "INSERT INTO indicator VALUES ('X', 'x', 'x', 'x', 'annual', 'sum', 1);",
    }
    for label, sql in checks.items():
        rejected, message = db.must_fail(sql)
        print(f"{'PASS' if rejected else 'FAIL'}  rejects {label}: {' '.join(message)}")
        results.append(rejected)

    passed = sum(bool(r) for r in results)
    print(f"\n{passed} of {len(results)} checks passed.")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
