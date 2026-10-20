"""Write database/load_data.sql from the processed CSV files.

The database is filled from the same cleaned files the dashboard reads
(data/processed/), so there is no second data pipeline. The output is a
plain SQL file of INSERT statements: loading it needs only the `mysql`
command-line client, no Python database driver and no password in code.

Run from the project root:
    python database/build_load_script.py
Then load it (after schema.sql):
    mysql -u <user> -p < database/load_data.sql
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = Path(__file__).resolve().parent / "load_data.sql"

SOURCES = [
    # id, name, publisher, url, raw file, last updated (None = not stated)
    (1, "World Development Indicators", "World Bank",
     "https://data.worldbank.org", "world_bank_*.xls", "2026-10-08"),
    (2, "COVID-19 cases and deaths", "WHO, via Our World in Data",
     "https://ourworldindata.org/coronavirus", "daily_cases_deaths_per_million.csv", None),
    (3, "COVID-19 Stringency Index",
     "Oxford COVID-19 Government Response Tracker (Blavatnik School of Government), via Our World in Data",
     "https://ourworldindata.org/covid-stringency-index", "covid-19-stringency-index.zip", "2024-08-01"),
]

INDICATORS = [
    # code, processed column, name, unit, frequency, yearly aggregation, source
    ("NY.GDP.MKTP.KD.ZG", "gdp_growth_pct", "GDP growth (annual %)",
     "% change in real GDP", "annual", "none", 1),
    ("FP.CPI.TOTL.ZG", "inflation_pct", "Inflation, consumer prices (annual %)",
     "% change in consumer prices", "annual", "none", 1),
    ("SL.UEM.TOTL.ZS", "unemployment_pct",
     "Unemployment, total (% of labour force, modelled ILO estimate)",
     "% of labour force", "annual", "none", 1),
    ("COVID.NEW_CASES_PM", "new_cases_per_million", "New COVID-19 cases per million (monthly total)",
     "cases per million people", "monthly", "sum", 2),
    ("COVID.NEW_DEATHS_PM", "new_deaths_per_million", "New COVID-19 deaths per million (monthly total)",
     "deaths per million people", "monthly", "sum", 2),
    ("OXCGRT.STI_VAX", "sti_vaccinated", "Stringency index for vaccinated people (monthly mean)",
     "index 0-100", "monthly", "mean", 3),
    ("OXCGRT.STI_NONVAX", "sti_nonvaccinated", "Stringency index for non-vaccinated people (monthly mean)",
     "index 0-100", "monthly", "mean", 3),
    ("OXCGRT.STI_WEIGHTED", "sti_weighted", "Stringency index, weighted average (monthly mean)",
     "index 0-100", "monthly", "mean", 3),
]

ANNUAL_FILES = {
    "gdp_growth_pct": "gdp_growth_pct_annual.csv",
    "inflation_pct": "inflation_pct_annual.csv",
    "unemployment_pct": "unemployment_pct_annual.csv",
}


def read_processed(name):
    """Read a processed CSV whatever its separator.

    stringency_monthly.csv uses ';' and decimal commas (French Excel format),
    so it is read explicitly; the other files are detected automatically.
    """
    if name == "stringency_monthly.csv":
        return pd.read_csv(PROCESSED / name, sep=";", decimal=",", encoding="utf-8-sig")
    return pd.read_csv(PROCESSED / name, sep=None, engine="python", encoding="utf-8-sig")


def sql_text(value):
    """Quote a value for SQL (NULL for None)."""
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


def insert_rows(table, columns, rows, batch=200):
    """INSERT statements in batches of `batch` rows."""
    statements = []
    for start in range(0, len(rows), batch):
        values = ",\n".join(
            "(" + ", ".join(sql_text(v) for v in row) + ")"
            for row in rows[start:start + batch]
        )
        statements.append(f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n{values};")
    return statements


def collect_rows():
    """Return the rows for every table, read from data/processed/."""
    code_of = {code: column for code, column, *_ in INDICATORS}
    code_by_column = {column: code for code, column in code_of.items()}

    countries = {}
    annual = []
    for column, filename in ANNUAL_FILES.items():
        df = read_processed(filename)
        for row in df.itertuples(index=False):
            countries[row.code] = row.country
            value = getattr(row, column)
            if pd.notna(value):  # missing values are left out, never zero
                annual.append((row.code, code_by_column[column], int(row.year), round(float(value), 3)))

    monthly = []
    for filename in ["cases_deaths_monthly.csv", "stringency_monthly.csv"]:
        df = read_processed(filename)
        value_columns = [c for c in df.columns if c in code_by_column]
        for row in df.itertuples(index=False):
            countries[row.code] = row.country
            month_start = f"{row.month}-01"
            for column in value_columns:
                value = getattr(row, column)
                if pd.notna(value):
                    monthly.append(
                        (row.code, code_by_column[column], month_start, round(float(value), 3))
                    )

    country_rows = sorted(countries.items())
    return {
        "data_source": SOURCES,
        "country": country_rows,
        "indicator": INDICATORS,
        "annual_observation": sorted(annual),
        "monthly_observation": sorted(monthly),
    }


def build_sql():
    rows = collect_rows()
    parts = [
        "-- Generated by database/build_load_script.py from data/processed/.",
        "-- Do not edit by hand: re-run the script after the processed data change.",
        "-- Load after schema.sql:  mysql -u <user> -p < database/load_data.sql",
        "",
        "USE covid_economy;",
        "SET NAMES utf8mb4;",
        "START TRANSACTION;",
        "",
    ]
    columns = {
        "data_source": ["source_id", "source_name", "publisher", "url", "raw_file", "last_updated"],
        "country": ["country_code", "country_name"],
        "indicator": ["indicator_code", "column_name", "indicator_name", "unit",
                      "frequency", "yearly_aggregation", "source_id"],
        "annual_observation": ["country_code", "indicator_code", "year", "value"],
        "monthly_observation": ["country_code", "indicator_code", "month_start", "value"],
    }
    for table, table_rows in rows.items():
        parts.append(f"-- {table}: {len(table_rows)} rows")
        parts.extend(insert_rows(table, columns[table], [tuple(r) for r in table_rows]))
        parts.append("")
    parts.append("COMMIT;")
    return "\n".join(parts) + "\n", {t: len(r) for t, r in rows.items()}


def main():
    sql, counts = build_sql()
    OUTPUT.write_text(sql, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    for table, n in counts.items():
        print(f"  {table}: {n} rows")


if __name__ == "__main__":
    main()
