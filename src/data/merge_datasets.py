#!/usr/bin/env python3
"""
Merge the five processed datasets (stringency, cases/deaths, GDP growth,
inflation, unemployment) into two combined tables for analysis.

Why two tables
  Stringency and cases/deaths are published by month; GDP growth, inflation
  and unemployment are published by year (the World Bank does not publish
  them more often). So:
    - merged_dataset_by_month: one row per country/month. The monthly
      datasets are used as-is; the yearly economic indicators are repeated
      for every month of their year (the same annual figure for Jan, Feb, ... Dec).
    - merged_dataset_by_year: one row per country/year. The monthly datasets
      are aggregated up to a year (summed for cases/deaths, averaged for the
      stringency index); the yearly economic indicators are used as-is.

Common time period
  Different sources cover different spans (see each quality_report.md). Both
  merged tables only include the period covered by EVERY input dataset, so
  every row is complete for every variable. The shortest input -- the
  stringency index, Jan 2020 - Dec 2022 -- decides that period: 3 full years,
  2020-2022. If a future re-run of a source script changes its coverage, the
  common period printed in merge_quality_report.md will change too.

Output (in --out, default ./data/processed)
  merged_dataset_by_month.csv / .xlsx
    country, code, month, new_cases_per_million, new_deaths_per_million,
    sti_vaccinated, sti_nonvaccinated, sti_weighted,
    gdp_growth_pct, inflation_pct, unemployment_pct
  merged_dataset_by_year.csv / .xlsx
    country, code, year, new_cases_per_million, new_deaths_per_million,
    sti_vaccinated, sti_nonvaccinated, sti_weighted,
    gdp_growth_pct, inflation_pct, unemployment_pct
  merge_quality_report.md   the common period found and how each column was built

Usage
  python merge_datasets.py
  python merge_datasets.py --processed-dir data/processed --stringency-dir clean_stringency

Requires pandas >= 2.0 and openpyxl (pip install pandas openpyxl).
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

log = logging.getLogger("merge")

MONTHLY_VALUE_COLS = ["new_cases_per_million", "new_deaths_per_million",
                      "sti_vaccinated", "sti_nonvaccinated", "sti_weighted"]
ANNUAL_INDICATOR_COLS = ["gdp_growth_pct", "inflation_pct", "unemployment_pct"]
# how to turn 12 monthly values into 1 yearly value, per column
YEARLY_AGG = {"new_cases_per_million": "sum", "new_deaths_per_million": "sum",
              "sti_vaccinated": "mean", "sti_nonvaccinated": "mean", "sti_weighted": "mean"}


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

    def render(self) -> str:
        return "# Merged datasets - quality report\n" + "\n".join(self.lines) + "\n"


# ---------------------------------------------------------------------------
# 1. Load the five processed datasets
# ---------------------------------------------------------------------------

def load_stringency_monthly(stringency_dir: Path) -> pd.DataFrame:
    # Written by clean_stringency.py in the French Excel format: ';' separator, ',' decimal
    path = stringency_dir / "stringency_monthly.csv"
    df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
    df["month"] = df["month"].astype(str)
    return df


def load_cases_deaths_monthly(processed_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(processed_dir / "cases_deaths" / "cases_deaths_monthly.csv")
    df["month"] = df["month"].astype(str)
    return df


def load_annual_indicator(processed_dir: Path, folder: str, filename: str) -> pd.DataFrame:
    return pd.read_csv(processed_dir / folder / filename)


def load_all(processed_dir: Path, stringency_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        "stringency": load_stringency_monthly(stringency_dir),
        "cases_deaths": load_cases_deaths_monthly(processed_dir),
        "gdp_growth": load_annual_indicator(processed_dir, "gdp_growth", "gdp_growth_pct_annual.csv"),
        "inflation": load_annual_indicator(processed_dir, "inflation", "inflation_pct_annual.csv"),
        "unemployment": load_annual_indicator(processed_dir, "unemployment", "unemployment_pct_annual.csv"),
    }


# ---------------------------------------------------------------------------
# 2. Find the common period and the common countries
# ---------------------------------------------------------------------------

def common_countries(data: dict[str, pd.DataFrame], report: Report) -> list[str]:
    code_sets = {name: set(df["code"]) for name, df in data.items()}
    common = set.intersection(*code_sets.values())
    for name, codes in code_sets.items():
        extra = codes - common
        if extra:
            report.warn(f"'{name}' has countries no other dataset has, excluded from the merge: {sorted(extra)}")
    report.add(f"Countries present in all 5 datasets: {sorted(common)}")
    return sorted(common)


def common_month_range(stringency: pd.DataFrame, cases_deaths: pd.DataFrame, report: Report) -> tuple[str, str]:
    bounds = {"stringency": (stringency["month"].min(), stringency["month"].max()),
             "cases_deaths": (cases_deaths["month"].min(), cases_deaths["month"].max())}
    start = max(b[0] for b in bounds.values())
    end = min(b[1] for b in bounds.values())
    report.add("Month coverage per monthly dataset: " +
               "; ".join(f"{name} {lo} to {hi}" for name, (lo, hi) in bounds.items()))
    report.add(f"Common monthly period (intersection, used for both merged tables): {start} to {end}")
    return start, end


# ---------------------------------------------------------------------------
# 3. Build the monthly table
# ---------------------------------------------------------------------------

def build_monthly(data: dict[str, pd.DataFrame], countries: list[str],
                  start: str, end: str, report: Report) -> pd.DataFrame:
    months = pd.period_range(start, end, freq="M").strftime("%Y-%m")
    grid = pd.MultiIndex.from_product([countries, months], names=["code", "month"]).to_frame(index=False)
    grid["year"] = grid["month"].str[:4].astype(int)

    merged = grid.merge(data["stringency"][["code", "month", *["sti_vaccinated", "sti_nonvaccinated", "sti_weighted"]]],
                        on=["code", "month"], how="left")
    merged = merged.merge(data["cases_deaths"][["code", "month", "new_cases_per_million", "new_deaths_per_million"]],
                          on=["code", "month"], how="left")
    for name, col in [("gdp_growth", "gdp_growth_pct"), ("inflation", "inflation_pct"),
                      ("unemployment", "unemployment_pct")]:
        merged = merged.merge(data[name][["code", "year", col]], on=["code", "year"], how="left")

    country_names = data["cases_deaths"][["code", "country"]].drop_duplicates()
    merged = merged.merge(country_names, on="code", how="left")

    cols = ["country", "code", "month", *MONTHLY_VALUE_COLS, *ANNUAL_INDICATOR_COLS]
    merged = merged[cols].sort_values(["code", "month"], kind="stable").reset_index(drop=True)

    missing = merged[cols[3:]].isna().sum()
    report.add(f"Monthly table: {len(merged):,} rows ({len(countries)} countries x "
               f"{len(months)} months), {merged.shape[1]} columns")
    if missing.any():
        report.warn(f"Missing values after merge (should be none inside the common period): "
                    f"{missing[missing > 0].to_dict()}")
    else:
        report.add("No missing values inside the common period")
    return merged


# ---------------------------------------------------------------------------
# 4. Build the yearly table
# ---------------------------------------------------------------------------

def monthly_to_yearly(monthly: pd.DataFrame, report: Report) -> pd.DataFrame:
    """Aggregate the monthly columns up to one row per country/year.

    A year is only aggregated if every one of its months has a value for that
    column; otherwise the yearly value is left missing, so a partial year is
    never mistaken for a complete yearly total or average.
    """
    monthly = monthly.assign(year=monthly["month"].str[:4].astype(int))
    g = monthly.groupby(["country", "code", "year"], sort=False)
    months_per_year = g.size()                       # months found per country/year
    present_per_col = g[list(YEARLY_AGG)].count()     # non-missing months per column

    sum_cols = [c for c, how in YEARLY_AGG.items() if how == "sum"]
    mean_cols = [c for c, how in YEARLY_AGG.items() if how == "mean"]
    values = pd.concat([g[sum_cols].sum(min_count=1), g[mean_cols].mean()], axis=1)[list(YEARLY_AGG)]

    incomplete = present_per_col.lt(months_per_year, axis=0)  # any month missing for that column
    values = values.mask(incomplete)
    yearly = values.reset_index()
    for col in ["sti_vaccinated", "sti_nonvaccinated", "sti_weighted"]:
        yearly[col] = yearly[col].round(2)
    for col in ["new_cases_per_million", "new_deaths_per_million"]:
        yearly[col] = yearly[col].round(3)
    incomplete = int(yearly[list(YEARLY_AGG)].isna().any(axis=1).sum())
    report.add(f"Years aggregated from complete monthly data: {len(yearly) - incomplete} of {len(yearly)} "
               f"(country-years with any missing month are left missing, not partially summed)")
    return yearly


def build_yearly(monthly: pd.DataFrame, data: dict[str, pd.DataFrame], report: Report) -> pd.DataFrame:
    yearly = monthly_to_yearly(monthly, report)
    for name, col in [("gdp_growth", "gdp_growth_pct"), ("inflation", "inflation_pct"),
                      ("unemployment", "unemployment_pct")]:
        yearly = yearly.merge(data[name][["code", "year", col]], on=["code", "year"], how="left")

    cols = ["country", "code", "year", *MONTHLY_VALUE_COLS, *ANNUAL_INDICATOR_COLS]
    yearly = yearly[cols].sort_values(["code", "year"], kind="stable").reset_index(drop=True)

    missing = yearly[cols[3:]].isna().sum()
    report.add(f"Yearly table: {len(yearly):,} rows ({yearly['code'].nunique()} countries x "
               f"{yearly['year'].nunique()} years), {yearly.shape[1]} columns")
    if missing.any():
        report.warn(f"Missing values after merge: {missing[missing > 0].to_dict()}")
    else:
        report.add("No missing values inside the common period")
    return yearly


# ---------------------------------------------------------------------------
# 5. Write and orchestrate
# ---------------------------------------------------------------------------

def write_table(df: pd.DataFrame, out_dir: Path, name: str, period_col: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / f"{name}.csv", index=False)
    if importlib.util.find_spec("openpyxl"):
        path = out_dir / f"{name}.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as xw:
            df.to_excel(xw, index=False, sheet_name=name[:31])
            ws = xw.sheets[name[:31]]
            ws.freeze_panes = "A2"
            for i, colname in enumerate(df.columns, start=1):
                letter = ws.cell(row=1, column=i).column_letter
                width = max(len(colname), df[colname].astype(str).str.len().max()
                           if colname in ("country", "code", period_col) else 10)
                ws.column_dimensions[letter].width = width + 2
        log.info("Wrote %s", path.resolve())
    else:
        log.warning("openpyxl not installed, Excel file for %s skipped (pip install openpyxl)", name)
    log.info("Wrote %s.csv to %s", name, out_dir.resolve())


def run_pipeline(processed_dir: Path, stringency_dir: Path, out_dir: Path,
                 verbose: bool = True) -> dict[str, pd.DataFrame]:
    if verbose and not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = Report()

    report.section("1. Load")
    data = load_all(processed_dir, stringency_dir)
    for name, df in data.items():
        report.add(f"Loaded '{name}': {len(df):,} rows")

    report.section("2. Common countries and period")
    countries = common_countries(data, report)
    start, end = common_month_range(data["stringency"], data["cases_deaths"], report)

    report.section("3. Monthly table")
    monthly = build_monthly(data, countries, start, end, report)

    report.section("4. Yearly table")
    yearly = build_yearly(monthly, data, report)

    write_table(monthly, out_dir, "merged_dataset_by_month", "month")
    write_table(yearly, out_dir, "merged_dataset_by_year", "year")
    (out_dir / "merge_quality_report.md").write_text(report.render(), encoding="utf-8")
    log.info("Wrote merge_quality_report.md to %s", out_dir.resolve())

    return {"merged_dataset_by_month": monthly, "merged_dataset_by_year": yearly}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--processed-dir", default="data/processed",
                   help="Folder with cases_deaths/, gdp_growth/, inflation/, unemployment/ (default: data/processed)")
    p.add_argument("--stringency-dir", default="clean_stringency",
                   help="Folder with stringency_monthly.csv (default: clean_stringency)")
    p.add_argument("--out", default="data/processed", help="Output folder (default: data/processed)")
    p.add_argument("-q", "--quiet", action="store_true")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO, format="%(message)s")
    run_pipeline(Path(a.processed_dir), Path(a.stringency_dir), Path(a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
