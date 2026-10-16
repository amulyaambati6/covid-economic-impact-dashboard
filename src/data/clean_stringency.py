#!/usr/bin/env python3
"""
Cleaning pipeline for the Our World in Data "COVID-19: Stringency Index" data
package (Oxford COVID-19 Government Response Tracker, OxCGRT).

Input columns
  Entity, Code, Day, Vaccinated, Non-vaccinated,
  Weighted average of vaccinated and non-vaccinated

What the index is
  A 0-100 score of how STRICT a government's containment rules were on a day
  (school/work closures, gathering limits, stay-at-home orders, travel controls...).
  It says nothing about whether the rules worked or were respected.

What the script does
  1. Load (CSV or xlsx; ',' or ';' separator; decimal comma OK); map headers by pattern
  2. Keep only the target countries (default: United States, India, France, China,
     Brazil, Germany, Rwanda), matched by ISO-3 code, ISO-2 code or name variants
  3. Parse dates and numbers, trim text, drop empty/undated rows, merge duplicates
  4. Set values outside 0-100 to missing; flag rows where the weighted index is not
     between the vaccinated and non-vaccinated ones, or vaccinated > non-vaccinated
  5. Report missing days (they are not filled: the monthly mean uses observed days)
  6. Aggregate to months with the MEAN of each index (rounded to 2 decimals).
     A month with fewer than --min-days observed days (default 15) is left empty.

Why the mean: the index is a level, not a flow, so summing days is meaningless.
With one row per day the mean is a time-weighted average strictness for the month.

Output: 6 columns
  country, code, month, sti_vaccinated, sti_nonvaccinated, sti_weighted

Files (in --out, default ./clean_stringency)
  stringency_monthly.xlsx  open this one in Excel: numbers are real numeric cells,
                           month is a real date shown as YYYY-MM
  stringency_monthly.csv   for Python/pandas (month as "YYYY-MM", decimal point)
  quality_report.md        every check, count and change

Usage
  python clean_stringency.py covid-stringency-index.csv
  python clean_stringency.py data.csv --out clean_stringency
  python clean_stringency.py data.csv --countries USA,FRA,MAR --min-days 20

In a notebook
  from clean_stringency import run_pipeline
  monthly = run_pipeline("covid-stringency-index.csv")["stringency_monthly"]

Requires pandas >= 2.0 and openpyxl (pip install pandas openpyxl).
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger("stringency")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_COUNTRIES: dict[str, str] = {
    "USA": "United States", "IND": "India", "FRA": "France", "CHN": "China",
    "BRA": "Brazil", "DEU": "Germany", "RWA": "Rwanda",
}
ISO2_TO_ISO3 = {"US": "USA", "IN": "IND", "FR": "FRA", "CN": "CHN",
                "BR": "BRA", "DE": "DEU", "RW": "RWA"}
NAME_ALIASES = {  # lower-case name -> ISO-3
    "united states": "USA", "united states of america": "USA", "usa": "USA", "us": "USA",
    "etats-unis": "USA", "états-unis": "USA",
    "india": "IND", "inde": "IND", "france": "FRA",
    "china": "CHN", "people's republic of china": "CHN", "chine": "CHN",
    "brazil": "BRA", "brasil": "BRA", "brésil": "BRA", "bresil": "BRA",
    "germany": "DEU", "allemagne": "DEU", "deutschland": "DEU",
    "rwanda": "RWA",
}

# Order matters: "Weighted average of vaccinated and non-vaccinated" and
# "Non-vaccinated" both contain "vaccinated", so the specific ones match first.
COLUMN_PATTERNS: dict[str, str] = {
    "country": r"^(entity|country|location)$",
    "code": r"^(code|iso.?code|iso3?)$",
    "date": r"^(day|date)$",
    "sti_weighted": r"weight|average",
    "sti_nonvax": r"^non.?vacc|^nonvax$|^nv$",
    "sti_vax": r"^vacc|^vax$|^v$",
}
INDEX_COLS = ["sti_weighted", "sti_nonvax", "sti_vax"]
LABELS = {"sti_weighted": "weighted", "sti_nonvax": "non-vaccinated", "sti_vax": "vaccinated"}
TOL = 0.05  # index points, absorbs rounding in the published values


@dataclass
class Config:
    countries: dict[str, str | None] = field(default_factory=lambda: dict(DEFAULT_COUNTRIES))
    min_days: int = 15  # a monthly mean needs at least this many observed days


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

    def render(self) -> str:
        return "# Stringency index - quality report\n" + "\n".join(self.lines) + "\n"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_numbers(raw: pd.Series) -> pd.Series:
    """Text -> float. Handles '45.37', '45,37' (French Excel), spaces."""
    s = raw.astype("string").str.strip().str.replace(r"[\s  %]", "", regex=True)
    has_comma = s.str.contains(",", regex=False).fillna(False)
    has_dot = s.str.contains(".", regex=False).fillna(False)
    s = s.mask(has_comma & has_dot, s.str.replace(",", "", regex=False))
    s = s.mask(has_comma & ~has_dot, s.str.replace(",", ".", regex=False))
    return pd.to_numeric(s.astype(object), errors="coerce").astype("float64")


def parse_dates(raw: pd.Series) -> tuple[pd.Series, str]:
    """Text -> datetime. Handles ISO, dd/mm/yyyy, mm/dd/yyyy and Excel serials."""
    s = raw.astype("string").str.strip().str.slice(0, 10)
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    formats = []
    iso = s.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
    if iso.any():
        out[iso] = pd.to_datetime(s[iso], format="%Y-%m-%d", errors="coerce")
        formats.append("YYYY-MM-DD")
    slash = s.str.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}").fillna(False)
    if slash.any():
        parts = s[slash].str.split("/", expand=True).astype(int)
        month_first = bool((parts[1] > 12).any() and not (parts[0] > 12).any())
        fmt = "%m/%d/%Y" if month_first else "%d/%m/%Y"
        out[slash] = pd.to_datetime(s[slash], format=fmt, errors="coerce")
        formats.append("MM/DD/YYYY" if month_first else "DD/MM/YYYY")
    serial = s.str.fullmatch(r"\d{5}(\.0+)?").fillna(False)
    if serial.any():
        out[serial] = pd.to_datetime(pd.to_numeric(s[serial].astype(object)),
                                     unit="D", origin="1899-12-30")
        formats.append("Excel serial")
    return out, ", ".join(formats) or "none recognised"


# ---------------------------------------------------------------------------
# 1. Load and standardise
# ---------------------------------------------------------------------------

def load_raw(path: Path, report: Report) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        df = pd.read_excel(path, dtype=str)
        report.add(f"Read Excel file `{path.name}`: {len(df):,} rows x {df.shape[1]} columns")
        return df
    for enc in ("utf-8-sig", "cp1252"):
        try:
            with open(path, encoding=enc) as fh:
                header = fh.readline()
            sep = ";" if header.count(";") > header.count(",") else ","
            df = pd.read_csv(path, sep=sep, dtype=str, encoding=enc,
                             keep_default_na=False, na_values=["", "NaN", "nan", "NULL"])
        except UnicodeDecodeError:
            continue
        report.add(f"Read CSV `{path.name}` (separator `{sep}`, encoding {enc}): "
                   f"{len(df):,} rows x {df.shape[1]} columns")
        return df
    raise ValueError(f"Could not decode {path} as UTF-8 or Windows-1252")


def standardize_columns(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    mapping: dict[str, str] = {}
    for new, pattern in COLUMN_PATTERNS.items():
        hits = [c for c in df.columns
                if c not in mapping and re.search(pattern, str(c).strip(), re.I)]
        if hits:
            mapping[hits[0]] = new
    report.add("Column mapping: " + "; ".join(f"`{o}` -> `{n}`" for o, n in mapping.items()))
    extra = [c for c in df.columns if c not in mapping]
    if extra:
        report.add(f"Ignored columns: {extra}")
    df = df.rename(columns=mapping)

    if "country" not in df and "code" not in df:
        raise KeyError(f"Need an Entity or Code column; found {list(mapping) + extra}")
    if "date" not in df:
        raise KeyError("No Day/Date column found")
    for c in ("country", "code"):
        if c not in df:
            df[c] = pd.NA
    missing = [c for c in INDEX_COLS if c not in df]
    if len(missing) == len(INDEX_COLS):
        raise KeyError(f"None of the three index columns found; columns: {list(mapping) + extra}")
    for c in missing:
        df[c] = pd.NA
        report.warn(f"Column for the {LABELS[c]} index not found; kept empty")
    return df[["country", "code", "date", *INDEX_COLS]].copy()


# ---------------------------------------------------------------------------
# 2. Countries
# ---------------------------------------------------------------------------

def filter_countries(df: pd.DataFrame, cfg: Config, report: Report) -> pd.DataFrame:
    targets = {k.upper(): v for k, v in cfg.countries.items()}
    df["country"] = df["country"].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    code = df["code"].astype("string").str.strip().str.upper().replace(ISO2_TO_ISO3)

    by_code = code.where(code.isin(list(targets)))
    name_map = {n: c for n, c in NAME_ALIASES.items() if c in targets}
    name_map.update({v.lower(): k for k, v in targets.items() if v})
    by_name = df["country"].str.lower().map(name_map)
    resolved = by_code.fillna(by_name).astype("string")

    via_name = resolved.notna() & by_code.isna()
    if via_name.any():
        pairs = (df.loc[via_name, "country"].astype(str) + " -> " + resolved[via_name].astype(str)).unique()
        report.add(f"Matched by name (no usable code): {sorted(pairs)}")

    n_entities = df["country"].nunique()
    df = df.loc[resolved.notna()].copy()
    df["code"] = resolved[resolved.notna()]
    modal = df.groupby("code")["country"].agg(lambda x: x.mode().iat[0] if x.notna().any() else pd.NA)
    df["country"] = df["code"].map({c: targets.get(c) or modal.get(c) for c in df["code"].unique()})

    counts = df["code"].value_counts()
    report.add(f"Kept {len(df):,} rows for {counts.size} of {len(targets)} target countries "
               f"(out of {n_entities} entities in the file)")
    missing = [f"{c} ({targets[c] or '?'})" for c in targets if c not in counts.index]
    if missing:
        report.warn(f"Target countries not found in the file: {missing}. "
                    f"If you downloaded 'only selected data', re-download with 'full data'.")
    if df.empty:
        raise ValueError("None of the target countries were found in the file")
    return df


# ---------------------------------------------------------------------------
# 3. Types, invalid rows, duplicates
# ---------------------------------------------------------------------------

def clean_types(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    raw = df["date"]
    df["date"], fmt = parse_dates(raw)
    report.add(f"Date format(s): {fmt}; unparseable dates: {int((df['date'].isna() & raw.notna()).sum()):,}")
    for col in INDEX_COLS:
        raw = df[col]
        df[col] = parse_numbers(raw)
        bad = raw.notna() & raw.astype("string").str.strip().ne("") & df[col].isna()
        if bad.any():
            report.add(f"`{col}`: {int(bad.sum()):,} non-numeric values set to missing "
                       f"(e.g. {raw[bad].astype(str).unique()[:5].tolist()})")
    return df


def drop_invalid_rows(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    n = len(df)
    df = df[df["date"].notna()]
    report.add(f"Dropped {n - len(df):,} rows without a valid date")
    n = len(df)
    df = df[df[INDEX_COLS].notna().any(axis=1)]
    report.add(f"Dropped {n - len(df):,} rows where all three indices are empty")
    return df


def deduplicate(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    n = len(df)
    df = df.drop_duplicates()
    report.add(f"Removed {n - len(df):,} exact duplicate rows")
    key = ["code", "date"]
    dup = df.duplicated(key, keep=False)
    if dup.any():
        conflicts = (df[dup].groupby(key)[INDEX_COLS].nunique() > 1).any(axis=1)
        report.add(f"{int(dup.sum()):,} rows share a (country, day) with another row; merged keeping "
                   f"the first non-missing value per column ({int(conflicts.sum()):,} had conflicting values)")
        df = df.groupby(key, as_index=False, sort=False).first()
    return df.sort_values(key, kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Validity and consistency
# ---------------------------------------------------------------------------

def validate(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    for col in INDEX_COLS:
        bad = (df[col] < 0) | (df[col] > 100)
        if bad.any():
            ex = df.loc[bad, ["code", "date", col]].head(3).astype(str).to_dict("records")
            report.add(f"`{col}`: {int(bad.sum()):,} values outside 0-100 set to missing, e.g. {ex}")
            df.loc[bad, col] = np.nan

    v, nv, w = df["sti_vax"], df["sti_nonvax"], df["sti_weighted"]
    lo, hi = np.fmin(v, nv), np.fmax(v, nv)
    df["flag_weighted_outside"] = v.notna() & nv.notna() & w.notna() & ((w < lo - TOL) | (w > hi + TOL))
    df["flag_vax_stricter"] = v.notna() & nv.notna() & (v > nv + TOL)
    df["differentiated"] = v.notna() & nv.notna() & (nv - v > TOL)  # looser rules for vaccinated

    # The weighted index is an average of the other two, so it cannot fall outside them.
    n_out = int(df["flag_weighted_outside"].sum())
    df.loc[df["flag_weighted_outside"], "sti_weighted"] = np.nan
    report.add(f"Weighted index outside [vaccinated, non-vaccinated] on {n_out:,} rows: "
               f"impossible for an average, set to missing (flag kept)")
    report.add(f"Vaccinated stricter than non-vaccinated on {int(df['flag_vax_stricter'].sum()):,} rows "
               f"(should not happen; flagged, kept)")

    diff = df[df["differentiated"]].groupby("country")["date"].agg(["min", "max", "size"])
    if diff.empty:
        report.add("No country ever had different rules for vaccinated people: the three columns are identical")
    else:
        diff.columns = ["first_day", "last_day", "days"]
        report.add("Days with different rules for vaccinated vs non-vaccinated people:")
        report.block(diff.to_string())
    return df


def report_coverage(df: pd.DataFrame, report: Report) -> None:
    rows = []
    for (code, country), g in df.groupby(["code", "country"], sort=True):
        span = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
        rows.append({"code": code, "country": country,
                     "first_day": g["date"].min().date(), "last_day": g["date"].max().date(),
                     "days": len(g), "missing_days": len(span) - len(g),
                     **{f"empty_{LABELS[c]}": int(g[c].isna().sum()) for c in INDEX_COLS}})
    cov = pd.DataFrame(rows)
    report.add("Coverage per country (missing days are not filled; monthly means use the days observed):")
    report.block(cov.to_string(index=False))
    if cov["last_day"].nunique() > 1:
        report.warn("Countries end on different days; compare them over a common period")


# ---------------------------------------------------------------------------
# 5. Monthly aggregation
# ---------------------------------------------------------------------------

OUTPUT_NAMES = {"sti_vax": "sti_vaccinated", "sti_nonvax": "sti_nonvaccinated",
                "sti_weighted": "sti_weighted"}
OUTPUT_COLS = ["country", "code", "month", "sti_vaccinated", "sti_nonvaccinated", "sti_weighted"]


def build_monthly(daily: pd.DataFrame, cfg: Config, report: Report) -> pd.DataFrame:
    """One row per country and month: the mean of each index over the observed days."""
    d = daily.assign(period=daily["date"].dt.to_period("M"))
    g = d.groupby(["country", "code", "period"], sort=True)
    means = g[INDEX_COLS].mean()
    counts = g[INDEX_COLS].count()
    days = g.size()

    thin = counts < cfg.min_days
    blanked = int((thin & means.notna()).to_numpy().sum())
    means = means.mask(thin).round(2)

    periods = days.index.get_level_values("period")
    partial = days[days.to_numpy() < periods.days_in_month]
    if partial.empty:
        report.add("Every month is complete (one row per day)")
    else:
        listed = [f"{code} {p} ({n}/{p.days_in_month} days)" for (_, code, p), n in partial.items()]
        report.add(f"Months with missing days (mean uses the days present): {listed}")
    report.add(f"Monthly values left empty for having fewer than {cfg.min_days} observed days: {blanked:,}")

    m = means.reset_index()
    m["month"] = m["period"].dt.start_time  # real date (1st of the month)
    m = m.rename(columns=OUTPUT_NAMES)[OUTPUT_COLS]
    m["country"] = m["country"].astype(str)
    m["code"] = m["code"].astype(str)
    for c in OUTPUT_COLS[3:]:
        m[c] = m[c].astype("float64")
    report.add(f"Monthly table: {len(m):,} rows x {m.shape[1]} columns "
               f"({m['country'].nunique()} countries, {m['month'].min():%Y-%m} to {m['month'].max():%Y-%m})")
    return m


# ---------------------------------------------------------------------------
# 6. Write and orchestrate
# ---------------------------------------------------------------------------

def write_outputs(monthly: pd.DataFrame, out_dir: Path, excel_fr: bool, report: Report) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Excel file: numbers written as numeric cells and months as date cells, so Excel
    # never has to guess them from text (which is what turns them into text values).
    if importlib.util.find_spec("openpyxl"):
        path = out_dir / "stringency_monthly.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as xw:
            monthly.to_excel(xw, index=False, sheet_name="monthly")
            ws = xw.sheets["monthly"]
            ws.freeze_panes = "A2"
            for i, name in enumerate(monthly.columns, start=1):
                letter = ws.cell(row=1, column=i).column_letter
                width = max(len(name), monthly[name].astype(str).str.len().max() if name in ("country", "code") else 10)
                ws.column_dimensions[letter].width = width + 2
            for row in ws.iter_rows(min_row=2):
                row[2].number_format = "yyyy-mm"
                for cell in row[3:]:
                    cell.number_format = "0.00"
        log.info("Wrote %s", path.resolve())
    else:
        report.warn("openpyxl not installed, Excel file skipped (pip install openpyxl)")

    # CSV for Python: month as YYYY-MM text, decimal point (or ';' + ',' with --excel-fr)
    csv = monthly.assign(month=monthly["month"].dt.strftime("%Y-%m"))
    kw: dict = dict(index=False)
    if excel_fr:
        kw.update(sep=";", decimal=",", encoding="utf-8-sig")
    csv.to_csv(out_dir / "stringency_monthly.csv", **kw)
    (out_dir / "quality_report.md").write_text(report.render(), encoding="utf-8")
    log.info("Wrote stringency_monthly.csv and quality_report.md to %s", out_dir.resolve())


def run_pipeline(path: str | Path, out_dir: str | Path | None = "clean_stringency",
                 excel_fr: bool = False, cfg: Config | None = None,
                 verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Run every step and return the clean tables. out_dir=None skips writing."""
    if verbose and not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = cfg or Config()
    report = Report()

    report.section("1. Load")
    df = load_raw(Path(path), report)
    df = standardize_columns(df, report)

    report.section("2. Countries")
    df = filter_countries(df, cfg, report)

    report.section("3. Types, rows, duplicates")
    df = clean_types(df, report)
    df = drop_invalid_rows(df, report)
    df = deduplicate(df, report)

    report.section("4. Validity and consistency")
    df = validate(df, report)
    report_coverage(df, report)

    report.section("5. Monthly aggregation")
    monthly = build_monthly(df, cfg, report)

    if out_dir is not None:
        write_outputs(monthly, Path(out_dir), excel_fr, report)
    # the cleaned daily rows are returned for notebook use but not written to disk
    return {"stringency_monthly": monthly, "stringency_daily": df}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="OWID stringency file (.csv or .xlsx)")
    p.add_argument("--out", default="clean_stringency", help="Output folder (default: clean_stringency)")
    p.add_argument("--countries", help="Comma-separated ISO-3 codes (default: USA,IND,FRA,CHN,BRA,DEU,RWA)")
    p.add_argument("--min-days", type=int, default=Config.min_days,
                   help="Minimum observed days for a monthly value (default: 15)")
    p.add_argument("--excel-fr", action="store_true",
                   help="Write the CSV with ';' and decimal ',' (the .xlsx needs no option)")
    p.add_argument("-q", "--quiet", action="store_true")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO, format="%(message)s")
    cfg = Config(min_days=a.min_days)
    if a.countries:
        codes = [c.strip().upper() for c in a.countries.split(",") if c.strip()]
        cfg.countries = {c: DEFAULT_COUNTRIES.get(c) for c in codes}
    run_pipeline(a.input, a.out, a.excel_fr, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())