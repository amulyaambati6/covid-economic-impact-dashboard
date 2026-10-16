#!/usr/bin/env python3
"""
Cleaning pipeline for the Our World in Data file "daily_cases_deaths_per_million"
(daily new confirmed COVID-19 cases and deaths per million people, WHO data).

Input columns
  Entity, Code, Day, New cases (per 1M), New deaths (per 1M)

What the script does
  1. Load (CSV or xlsx; ',' or ';' separator; decimal comma OK); map headers by pattern
  2. Keep only the target countries (default: United States, India, France, China,
     Brazil, Germany, Rwanda), matched by ISO-3 code, ISO-2 code or name variants
  3. Parse dates and numbers, trim text, drop empty/undated rows, merge duplicates
  4. Impossible values (> 1,000,000 per million in a day) set to missing;
     negative days (source revisions) are KEPT, because dropping them would
     overstate the totals
  5. Report missing days and how often each country actually reported
     (weekly reporting shows up as ~1 non-zero day in 7)
  6. Aggregate to months with the SUM of the daily values = total new cases
     (deaths) per million people in that month. A month with fewer than
     --min-days observed days (default 15) is left empty.

Why the sum: these are daily flows (new cases each day), so the monthly figure
is their total. Use --agg mean for the average per day instead.

Output: 5 columns. country, code and month use exactly the same names and
formats as clean_stringency.py, so the two monthly files merge directly.
  country, code, month, new_cases_per_million, new_deaths_per_million

Files (in --out, default ./clean_cases_deaths)
  cases_deaths_monthly.xlsx  open this one in Excel: real numeric cells, month as a date (YYYY-MM)
  cases_deaths_monthly.csv   for Python/pandas (month as "YYYY-MM", decimal point)
  quality_report.md          every check, count and change

Usage
  python clean_cases_deaths.py daily_cases_deaths_per_million.csv
  python clean_cases_deaths.py data.csv --agg mean
  python clean_cases_deaths.py data.csv --countries USA,FRA,MAR --min-days 20

In a notebook
  from clean_cases_deaths import run_pipeline
  monthly = run_pipeline("daily_cases_deaths_per_million.csv")["cases_deaths_monthly"]

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

log = logging.getLogger("cases_deaths")

# ---------------------------------------------------------------------------
# Configuration (country list and names identical to clean_stringency.py)
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

# Value columns: skip smoothed / cumulative variants if the download contains them.
_NOT_RAW = r"^(?!.*(smooth|average|7.?day|rolling|total|cumul|weekly)).*"
COLUMN_PATTERNS: dict[str, str] = {
    "country": r"^(entity|country|location)$",
    "code": r"^(code|iso.?code|iso3?)$",
    "date": r"^(day|date)$",
    "new_cases": _NOT_RAW + r"case",
    "new_deaths": _NOT_RAW + r"death",
}
VALUE_COLS = ["new_cases", "new_deaths"]
LABELS = {"new_cases": "new cases", "new_deaths": "new deaths"}
MAX_PER_MILLION_PER_DAY = 1_000_000  # more than the whole population in one day

OUTPUT_NAMES = {"new_cases": "new_cases_per_million", "new_deaths": "new_deaths_per_million"}
OUTPUT_COLS = ["country", "code", "month", "new_cases_per_million", "new_deaths_per_million"]
DECIMALS = 3  # monthly deaths per million can be well below 0.01


@dataclass
class Config:
    countries: dict[str, str | None] = field(default_factory=lambda: dict(DEFAULT_COUNTRIES))
    agg: str = "sum"    # sum (monthly total) | mean (average per day)
    min_days: int = 15  # a monthly value needs at least this many observed days


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
        return "# Cases and deaths - quality report\n" + "\n".join(self.lines) + "\n"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_numbers(raw: pd.Series) -> pd.Series:
    """Text -> float. Handles '12.5', '12,5' (French Excel), '1,234.5', spaces."""
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
        # prefer the per-million version if the file has both
        hits.sort(key=lambda c: not re.search(r"per|million|1m", str(c), re.I))
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
    missing = [c for c in VALUE_COLS if c not in df]
    if len(missing) == len(VALUE_COLS):
        raise KeyError(f"No cases or deaths column found; columns: {list(mapping) + extra}")
    for c in missing:
        df[c] = pd.NA
        report.warn(f"Column for {LABELS[c]} not found; kept empty")
    for old, new in mapping.items():
        if new in VALUE_COLS and not re.search(r"per|million|1m", str(old), re.I):
            report.warn(f"`{old}` does not say 'per million': check the unit before "
                        f"trusting the column name `{OUTPUT_NAMES[new]}`")
    return df[["country", "code", "date", *VALUE_COLS]].copy()


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
    for col in VALUE_COLS:
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
    df = df[df[VALUE_COLS].notna().any(axis=1)]
    report.add(f"Dropped {n - len(df):,} rows where both values are empty")
    return df


def deduplicate(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    n = len(df)
    df = df.drop_duplicates()
    report.add(f"Removed {n - len(df):,} exact duplicate rows")
    key = ["code", "date"]
    dup = df.duplicated(key, keep=False)
    if dup.any():
        conflicts = (df[dup].groupby(key)[VALUE_COLS].nunique() > 1).any(axis=1)
        report.add(f"{int(dup.sum()):,} rows share a (country, day) with another row; merged keeping "
                   f"the first non-missing value per column ({int(conflicts.sum()):,} had conflicting values)")
        df = df.groupby(key, as_index=False, sort=False).first()
    return df.sort_values(key, kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Validity
# ---------------------------------------------------------------------------

def validate(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    for col in VALUE_COLS:
        bad = df[col] > MAX_PER_MILLION_PER_DAY
        if bad.any():
            ex = df.loc[bad, ["code", "date", col]].head(3).astype(str).to_dict("records")
            report.add(f"`{col}`: {int(bad.sum()):,} impossible values (more than the whole "
                       f"population in a day) set to missing, e.g. {ex}")
            df.loc[bad, col] = np.nan

        neg = df[col] < 0
        if neg.any():
            by = df.loc[neg].groupby("country").size().to_dict()
            report.add(f"`{col}`: {int(neg.sum()):,} negative days (the source revised its total "
                       f"down). Kept, so monthly totals stay correct: {by}")
    return df


def report_coverage(df: pd.DataFrame, report: Report) -> None:
    rows = []
    for (code, country), g in df.groupby(["code", "country"], sort=True):
        span = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
        rows.append({"code": code, "country": country,
                     "first_day": g["date"].min().date(), "last_day": g["date"].max().date(),
                     "days": len(g), "missing_days": len(span) - len(g),
                     **{f"empty_{c}": int(g[c].isna().sum()) for c in VALUE_COLS}})
    cov = pd.DataFrame(rows)
    report.add("Coverage per country (missing days are not filled):")
    report.block(cov.to_string(index=False))
    if cov["last_day"].nunique() > 1:
        report.warn("Countries end on different days; compare them over a common period")

    # How often a country actually reports: ~100% = daily, ~14% = weekly reporting
    share = (df.assign(year=df["date"].dt.year, reported=df["new_cases"].fillna(0).ne(0))
               .pivot_table(index="country", columns="year", values="reported", aggfunc="mean")
               .mul(100).round(0))
    report.add("Share of days with a non-zero case count (%). ~14% means weekly reporting: "
               "a week that crosses a month boundary is counted in the month of its report day.")
    report.block(share.to_string())


# ---------------------------------------------------------------------------
# 5. Monthly aggregation
# ---------------------------------------------------------------------------

def month_gaps(d: pd.DataFrame, days: pd.Series) -> tuple[list[str], list[str]]:
    """Split incomplete months into real gaps and months cut by the series start/end."""
    first = d.groupby("code")["date"].min()
    last = d.groupby("code")["date"].max()
    gaps, edges = [], []
    for (_, code, p), n in days.items():
        start = max(p.start_time, first[code])
        end = min(p.end_time.normalize(), last[code])
        expected = (end - start).days + 1
        if n < expected:
            gaps.append(f"{code} {p} ({n}/{expected} days)")
        elif expected < p.days_in_month:
            edges.append(f"{code} {p} (from {start:%d %b})" if start > p.start_time
                         else f"{code} {p} (until {end:%d %b})")
    return gaps, edges


def build_monthly(daily: pd.DataFrame, cfg: Config, report: Report) -> pd.DataFrame:
    """One row per country and month: sum (default) or mean of the daily values."""
    d = daily.assign(period=daily["date"].dt.to_period("M"))
    g = d.groupby(["country", "code", "period"], sort=True)
    values = g[VALUE_COLS].sum(min_count=1) if cfg.agg == "sum" else g[VALUE_COLS].mean()
    counts = g[VALUE_COLS].count()
    days = g.size()

    thin = counts < cfg.min_days
    blanked = int((thin & values.notna()).to_numpy().sum())
    values = values.mask(thin).round(DECIMALS)

    gaps, edges = month_gaps(d, days)
    if gaps:
        report.add(f"Months with missing days inside the series ({cfg.agg} uses the days present"
                   f"{', so these totals may be low' if cfg.agg == 'sum' else ''}): {gaps}")
    else:
        report.add("No missing days inside any series")
    if edges:
        report.add(f"Months only partly covered because a series starts or ends mid-month "
                   f"(not missing data): {edges}")
    report.add(f"Monthly values left empty for having fewer than {cfg.min_days} observed days: {blanked:,}")

    neg = (values < 0).any(axis=1)
    if neg.any():
        listed = [f"{c} {p}" for (_, c, p) in values.index[neg]]
        report.warn(f"Months with a negative total (revisions larger than new reports): {listed}")

    m = values.reset_index()
    m["month"] = m["period"].dt.start_time  # real date (1st of the month), same as clean_stringency.py
    m = m.rename(columns=OUTPUT_NAMES)[OUTPUT_COLS]
    m["country"] = m["country"].astype(str)
    m["code"] = m["code"].astype(str)
    for c in OUTPUT_COLS[3:]:
        m[c] = m[c].astype("float64")
    what = "total per month" if cfg.agg == "sum" else "average per day"
    report.add(f"Monthly table ({what}): {len(m):,} rows x {m.shape[1]} columns "
               f"({m['country'].nunique()} countries, {m['month'].min():%Y-%m} to {m['month'].max():%Y-%m})")
    return m


# ---------------------------------------------------------------------------
# 6. Write and orchestrate
# ---------------------------------------------------------------------------

def write_outputs(monthly: pd.DataFrame, out_dir: Path, excel_fr: bool, report: Report) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    num_fmt = "0." + "0" * DECIMALS

    # Excel file: numeric cells and date cells, so Excel never stores them as text.
    if importlib.util.find_spec("openpyxl"):
        path = out_dir / "cases_deaths_monthly.xlsx"
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
                    cell.number_format = num_fmt
        log.info("Wrote %s", path.resolve())
    else:
        report.warn("openpyxl not installed, Excel file skipped (pip install openpyxl)")

    # CSV for Python: month as YYYY-MM text, decimal point (or ';' + ',' with --excel-fr)
    csv = monthly.assign(month=monthly["month"].dt.strftime("%Y-%m"))
    kw: dict = dict(index=False)
    if excel_fr:
        kw.update(sep=";", decimal=",", encoding="utf-8-sig")
    csv.to_csv(out_dir / "cases_deaths_monthly.csv", **kw)
    (out_dir / "quality_report.md").write_text(report.render(), encoding="utf-8")
    log.info("Wrote cases_deaths_monthly.csv and quality_report.md to %s", out_dir.resolve())


def run_pipeline(path: str | Path, out_dir: str | Path | None = "clean_cases_deaths",
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

    report.section("4. Validity and coverage")
    df = validate(df, report)
    report_coverage(df, report)

    report.section("5. Monthly aggregation")
    monthly = build_monthly(df, cfg, report)

    if out_dir is not None:
        write_outputs(monthly, Path(out_dir), excel_fr, report)
    # the cleaned daily rows are returned for notebook use but not written to disk
    return {"cases_deaths_monthly": monthly, "cases_deaths_daily": df}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="OWID daily cases/deaths file (.csv or .xlsx)")
    p.add_argument("--out", default="clean_cases_deaths", help="Output folder (default: clean_cases_deaths)")
    p.add_argument("--countries", help="Comma-separated ISO-3 codes (default: USA,IND,FRA,CHN,BRA,DEU,RWA)")
    p.add_argument("--agg", choices=["sum", "mean"], default="sum",
                   help="sum = total per month (default); mean = average per day")
    p.add_argument("--min-days", type=int, default=Config.min_days,
                   help="Minimum observed days for a monthly value (default: 15)")
    p.add_argument("--excel-fr", action="store_true",
                   help="Write the CSV with ';' and decimal ',' (the .xlsx needs no option)")
    p.add_argument("-q", "--quiet", action="store_true")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO, format="%(message)s")
    cfg = Config(agg=a.agg, min_days=a.min_days)
    if a.countries:
        codes = [c.strip().upper() for c in a.countries.split(",") if c.strip()]
        cfg.countries = {c: DEFAULT_COUNTRIES.get(c) for c in codes}
    run_pipeline(a.input, a.out, a.excel_fr, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())