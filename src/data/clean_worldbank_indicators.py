#!/usr/bin/env python3
"""
Cleaning pipeline for the three World Bank indicator downloads: GDP growth,
inflation, and unemployment. All three files use the same World Bank
"Data" export format, so one script cleans all of them the same way.

Input format (World Bank "Data" sheet, header starts on row 4)
  Country Name, Country Code, Indicator Name, Indicator Code, 1960, 1961, ... latest year
  One row per country; one column per year; cell = indicator value for that
  country/year (or empty if the World Bank has no value).

What the script does, for each of the 3 files
  1. Load the "Data" sheet of the .xls file (requires the xlrd package)
  2. Keep only the target countries (default: United States, India, France,
     China, Brazil, Germany, Rwanda), matched by ISO-3 country code -- the
     same 7 countries used in clean_stringency.py and clean_deaths_cases.py
  3. Keep only the target years (default: 2018-2024)
  4. Reshape from "one column per year" (wide) to "one row per country-year"
     (long), which is the same shape as the other processed datasets
  5. Leave a missing cell as missing (NaN), never fill it with zero
  6. Report how many country-years are missing a value

Output: 4 columns. country, code and year use the same names as
clean_stringency.py and clean_deaths_cases.py (month -> year here, since
World Bank indicators are only published once a year), so all five
processed datasets merge directly.
  country, code, year, <value column, e.g. gdp_growth_pct>

Files (one subfolder per indicator under --out, default ./data/processed)
  <name>_annual.csv    for Python/pandas (decimal point)
  <name>_annual.xlsx   open this one in Excel: real numeric cells
  quality_report.md    every check, count and change

Usage
  python clean_worldbank_indicators.py
  python clean_worldbank_indicators.py --raw-dir data/raw --out data/processed
  python clean_worldbank_indicators.py --countries USA,FRA,MAR --years 2015-2024

Requires pandas >= 2.0, xlrd >= 2.0 (to read legacy .xls files) and openpyxl
(pip install pandas xlrd openpyxl).
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

log = logging.getLogger("worldbank")

# ---------------------------------------------------------------------------
# Configuration (country list and names identical to clean_stringency.py)
# ---------------------------------------------------------------------------

DEFAULT_COUNTRIES: dict[str, str] = {
    "USA": "United States", "IND": "India", "FRA": "France", "CHN": "China",
    "BRA": "Brazil", "DEU": "Germany", "RWA": "Rwanda",
}
DEFAULT_START_YEAR = 2018
DEFAULT_END_YEAR = 2024
WORLD_BANK_HEADER_ROW = 3  # the "Data" sheet has 3 title rows before the header


@dataclass
class Indicator:
    raw_file: str          # file name inside --raw-dir
    indicator_code: str    # World Bank code, used only to double check the file
    folder: str             # output subfolder name under --out
    value_name: str        # output column name and output file name
    label: str              # human-readable name for the report


INDICATORS: list[Indicator] = [
    Indicator("world_bank_gdp_growth.xls", "NY.GDP.MKTP.KD.ZG",
              "gdp_growth", "gdp_growth_pct", "GDP growth (annual %)"),
    Indicator("world_bank_inflation.xls", "FP.CPI.TOTL.ZG",
              "inflation", "inflation_pct", "Inflation, consumer prices (annual %)"),
    Indicator("world_bank_unemployment.xls", "SL.UEM.TOTL.ZS",
              "unemployment", "unemployment_pct", "Unemployment, total (% of labor force, modeled ILO estimate)"),
]


@dataclass
class Config:
    countries: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COUNTRIES))
    start_year: int = DEFAULT_START_YEAR
    end_year: int = DEFAULT_END_YEAR


@dataclass
class Report:
    lines: list[str] = field(default_factory=list)

    def section(self, title: str) -> None:
        self.lines.append(f"\n## {title}\n")

    def add(self, msg: str) -> None:
        log.info(msg)
        self.lines.append(f"- {msg}")

    def warn(self, msg: str) -> None:
        log.warning("WARNING: %s", msg)
        self.lines.append(f"- **WARNING:** {msg}")

    def block(self, text: str) -> None:
        self.lines.append(f"\n```\n{text}\n```\n")

    def render(self, title: str) -> str:
        return f"# {title} - quality report\n" + "\n".join(self.lines) + "\n"


# ---------------------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------------------

def load_data_sheet(path: Path, report: Report) -> pd.DataFrame:
    if not importlib.util.find_spec("xlrd"):
        raise ImportError("Reading .xls files needs xlrd >= 2.0.1 (pip install xlrd)")
    df = pd.read_excel(path, sheet_name="Data", header=WORLD_BANK_HEADER_ROW)
    report.add(f"Read `{path.name}`, sheet 'Data': {len(df):,} countries x {df.shape[1]} columns")
    return df


def check_indicator_code(df: pd.DataFrame, indicator: Indicator, report: Report) -> None:
    codes = set(df["Indicator Code"].dropna().unique())
    if codes != {indicator.indicator_code}:
        report.warn(f"Expected indicator code {indicator.indicator_code!r} but file has {sorted(codes)}; "
                    f"double check this is the right download before trusting `{indicator.value_name}`")


# ---------------------------------------------------------------------------
# 2 & 3. Countries and years, reshape wide -> long
# ---------------------------------------------------------------------------

def filter_and_reshape(df: pd.DataFrame, cfg: Config, indicator: Indicator, report: Report) -> pd.DataFrame:
    df = df[df["Country Code"].isin(cfg.countries)].copy()
    found = set(df["Country Code"])
    missing = [f"{c} ({n})" for c, n in cfg.countries.items() if c not in found]
    report.add(f"Kept {len(found)} of {len(cfg.countries)} target countries")
    if missing:
        report.warn(f"Target countries not found in the file: {missing}")
    if df.empty:
        raise ValueError("None of the target countries were found in the file")

    years = [str(y) for y in range(cfg.start_year, cfg.end_year + 1)]
    available_years = [y for y in years if y in df.columns]
    missing_years = [y for y in years if y not in df.columns]
    if missing_years:
        report.warn(f"Years not present in the file (outside what the World Bank published): {missing_years}")

    long = df.melt(
        id_vars=["Country Name", "Country Code"],
        value_vars=available_years,
        var_name="year",
        value_name=indicator.value_name,
    )
    long["year"] = long["year"].astype(int)
    long[indicator.value_name] = pd.to_numeric(long[indicator.value_name], errors="coerce").round(3)
    long = long.rename(columns={"Country Name": "country", "Country Code": "code"})
    long = long.sort_values(["code", "year"], kind="stable").reset_index(drop=True)
    return long[["country", "code", "year", indicator.value_name]]


def report_missing(df: pd.DataFrame, indicator: Indicator, report: Report) -> None:
    n_missing = int(df[indicator.value_name].isna().sum())
    report.add(f"Country-years with no published value for {indicator.label}: {n_missing} of {len(df):,} "
               f"(left as missing, not filled with zero)")
    if n_missing:
        rows = df[df[indicator.value_name].isna()][["country", "year"]]
        report.block(rows.to_string(index=False))


# ---------------------------------------------------------------------------
# 4. Write and orchestrate
# ---------------------------------------------------------------------------

def write_outputs(annual: pd.DataFrame, out_dir: Path, indicator: Indicator, report: Report) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    annual.to_csv(out_dir / f"{indicator.value_name}_annual.csv", index=False)

    if importlib.util.find_spec("openpyxl"):
        path = out_dir / f"{indicator.value_name}_annual.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as xw:
            annual.to_excel(xw, index=False, sheet_name="annual")
            ws = xw.sheets["annual"]
            ws.freeze_panes = "A2"
            for i, name in enumerate(annual.columns, start=1):
                letter = ws.cell(row=1, column=i).column_letter
                width = max(len(name), annual[name].astype(str).str.len().max() if name in ("country", "code") else 10)
                ws.column_dimensions[letter].width = width + 2
            for row in ws.iter_rows(min_row=2):
                row[3].number_format = "0.00"
        log.info("Wrote %s", path.resolve())
    else:
        report.warn("openpyxl not installed, Excel file skipped (pip install openpyxl)")

    (out_dir / "quality_report.md").write_text(report.render(indicator.label), encoding="utf-8")
    log.info("Wrote %s_annual.csv and quality_report.md to %s", indicator.value_name, out_dir.resolve())


def clean_one(raw_dir: Path, out_dir: Path, indicator: Indicator, cfg: Config,
             verbose: bool = True) -> pd.DataFrame:
    """Run every step for one indicator file and return the clean annual table."""
    report = Report()
    report.section("1. Load")
    df = load_data_sheet(raw_dir / indicator.raw_file, report)
    check_indicator_code(df, indicator, report)

    report.section("2. Countries and years")
    annual = filter_and_reshape(df, cfg, indicator, report)

    report.section("3. Missing values")
    report_missing(annual, indicator, report)

    write_outputs(annual, out_dir / indicator.folder, indicator, report)
    return annual


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw-dir", default="data/raw", help="Folder with the World Bank .xls downloads (default: data/raw)")
    p.add_argument("--out", default="data/processed", help="Output folder (default: data/processed)")
    p.add_argument("--countries", help="Comma-separated ISO-3 codes (default: USA,IND,FRA,CHN,BRA,DEU,RWA)")
    p.add_argument("--years", help="Year range as START-END (default: 2018-2024)")
    p.add_argument("-q", "--quiet", action="store_true")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO, format="%(message)s")
    cfg = Config()
    if a.countries:
        codes = [c.strip().upper() for c in a.countries.split(",") if c.strip()]
        cfg.countries = {c: DEFAULT_COUNTRIES.get(c, c) for c in codes}
    if a.years:
        start, end = (int(y) for y in a.years.split("-"))
        cfg.start_year, cfg.end_year = start, end

    raw_dir, out_dir = Path(a.raw_dir), Path(a.out)
    for indicator in INDICATORS:
        clean_one(raw_dir, out_dir, indicator, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
