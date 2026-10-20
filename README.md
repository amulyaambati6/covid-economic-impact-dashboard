# COVID-19 and the Global Economy
## Project Documentation

- [Team Planning Document (Google Docs)](https://docs.google.com/document/d/1mCDpxkIXW9CLHjlG38D0ouK-Z_i__Tn6C99cpsMyHT8/edit?usp=sharing)

CentraleDigitalLab Data Storytelling university project exploring how COVID-19 affected the global economy. The presentation is planned for 20 minutes by a team of four, with a deadline of October 21, 2026.

## Research question

**How did COVID-19 impact the global economy?**

The dashboard compares seven countries: the United States, India, France, China, Brazil, Germany, and Rwanda. Economic indicators (World Bank GDP growth, unemployment, and inflation) cover 2018–2024; COVID-19 cases, deaths, and government-response stringency cover 2020–2022, the period every source covers. The findings describe these seven countries only, not the whole world.

The headline findings are in [`findings_summary.md`](findings_summary.md), the single authoritative findings document. Its key figures are checked against the data by `tests/test_findings.py`.

## Setup

Activate the existing Conda environment in Anaconda Prompt or the VS Code terminal, then install the dependencies:

```powershell
conda activate covid-dashboard
python -m pip install -r requirements.txt
```

`requirements.txt` includes `scipy`, which the dashboard needs for its Spearman correlations. The app was tested with Python 3.12, Streamlit 1.66, pandas 3.0, Plotly 6.9, and SciPy 1.18.

## Run the app

From the project root:

```powershell
streamlit run app.py
```

Streamlit prints the local address (usually <http://localhost:8501>) to open in a browser. The app is a multi-page dashboard:

| Page | What it shows |
| --- | --- |
| **Home** | The research question, a hand-drawn-style virus-and-globe illustration, and six cards that open the research pages. Hovering the virus highlights the cards; every card also works by click, tap, and keyboard (Tab / Enter). |
| **Economic Growth** | GDP growth by year, 2020 growth against each country's 2018–2019 average, and a reconstructed GDP index against a pre-COVID trend. |
| **Labour Market** | Unemployment by year, the 2019–2020 change, and whether each country returned to its 2019 rate. |
| **Inflation** | Consumer price inflation by year, 2022 against each country's normal, and peak versus latest rates. |
| **Pandemic & Policy Response** | Reported cases and deaths (log, linear, or per-country scale), stringency lines and heatmap, rules by vaccination status, and exploratory correlations with Bonferroni-adjusted p-values and within-year checks. |
| **Country Comparisons** | Rank countries on any indicator and year, a summary table of the headline measures, and 2020 deaths against the GDP shortfall. |
| **Key Findings** | Headline results for all seven countries, calculated live, and a draft assessment of whether the data are sufficient. |
| Full report (one page) | All research pages on one scrolling page (the original single-page dashboard). |
| About & methods | Sources, method definitions, and limitations. |

The sidebar filters (countries and year range) apply to every research page and are kept when you move between pages. Each country keeps the same colour and marker on every chart. Every page ends with interpretation notes and data limitations.

**Design:** the theme in `.streamlit/config.toml` sets the ivory/blush/navy palette and the fonts (Source Serif 4 for headings, Inter for text; both load from Google Fonts and fall back to Georgia and the system sans-serif font without internet). `assets/style.css` styles the page components and the homepage illustration; `app.py` loads it on every page. The illustration is inline SVG generated in `pages/landing.py`, so there are no image files to load. Animations stop if the computer is set to reduce motion.

## Tests

Run all checks from the project root:

```powershell
python -m unittest discover -s tests
```

| Test file | What it checks |
| --- | --- |
| `tests/test_app_smoke.py` | The app and all nine pages start without errors; homepage cards link to the registered pages; KPIs; country and year filters, selectors, and scale options; country colours stay fixed on every chart and after filtering. |
| `tests/test_analysis.py` | The shared calculations in `src/analysis/`: country summary table, GDP index, recovery table, correlations and Bonferroni correction. |
| `tests/test_processed_data.py` | Seven countries, expected years and months, no duplicate keys, no missing values in the merged tables, value ranges, yearly totals equal monthly sums. |
| `tests/test_findings.py` | Key figures quoted in `findings_summary.md` recomputed from the processed data. |
| `tests/test_data_validation.py` | The `missing_years()` helper. |

## Check economic indicator coverage

The coverage script checks the three World Bank indicators across the seven countries for each year from 2019 through 2023. It requires internet access:

```powershell
python check_data_coverage.py
```

The script writes `data/processed/coverage_audit.csv`, one row per country, indicator, and year. The existing audit is preserved. Missing source values and request errors are marked separately; a request error means coverage is unverified, not proven missing. In the current audit the five Brazil inflation rows (2019–2023) are unverified because the request timed out; the downloaded World Bank file does contain those values.

World Bank Indicators API documentation: <https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation>
Our World in Data COVID-19 data documentation: <https://github.com/owid/covid-19-data/tree/master/public/data>

## Rebuild the processed data (optional)

The app reads the processed CSV files already committed in `data/processed/`, so you do **not** need to run this to use the app. To rebuild them from the raw files, run these commands from the project root (verified on 2026-10-20; the rebuilt values were identical to the committed ones):

```powershell
# 1. Stringency (OxCGRT via Our World in Data). Unzip the raw download first.
python -c "import zipfile; zipfile.ZipFile('data/raw/covid-19-stringency-index.zip').extractall('clean_stringency/input')"
python src/data/clean_stringency.py clean_stringency/input/covid-19-stringency-index.csv --out clean_stringency --excel-fr

# 2. Cases and deaths (WHO via Our World in Data)
python src/data/clean_deaths_cases.py data/raw/daily_cases_deaths_per_million.csv --out data/processed/cases_deaths

# 3. World Bank GDP growth, inflation, unemployment (2018-2024)
python src/data/clean_worldbank_indicators.py

# 4. Merge everything into the monthly and yearly tables the app reads
python src/data/merge_datasets.py

# 5. Copy the per-source tables to the top of data/processed/, where the app reads them
python -c "import shutil; [shutil.copy('data/processed/' + f, 'data/processed/') for f in ['gdp_growth/gdp_growth_pct_annual.csv', 'inflation/inflation_pct_annual.csv', 'unemployment/unemployment_pct_annual.csv', 'cases_deaths/cases_deaths_monthly.csv']]; shutil.copy('clean_stringency/stringency_monthly.csv', 'data/processed/')"
```

Notes:

- `--excel-fr` is required in step 1: `merge_datasets.py` reads the stringency file with `;` separators and decimal commas.
- Each cleaning script writes a `quality_report.md` next to its output; the merge writes `data/processed/merge_quality_report.md`.
- Stringency and cases/deaths are monthly; GDP growth, inflation, and unemployment are only published yearly by the World Bank. The by-month table repeats each year's economic figures across its 12 months; the by-year table sums (cases, deaths) or averages (stringency) the months. Both tables are limited to **2020–2022**, the period every input covers.
- Rebuilt CSV files use `,` separators, while some committed files were re-saved with `;`. The app and tests detect the separator automatically, so either works.
- `stringency.csv` in the project root is a re-saved copy of the CSV inside the stringency zip (same 202,760 rows, `;` separators, dd/mm/yyyy dates). Step 1 gives identical output from either file.
- `.xls` files need `xlrd` and the Excel outputs need `openpyxl` (both in `requirements.txt`).

## Exploratory notebook

`notebooks/COVID_economy_EDA.ipynb` contains the exploratory analysis behind `findings_summary.md`. It was written for Google Colab: the first data cell uploads the processed CSV files with `google.colab.files.upload()`. To run it locally, skip that cell and put the processed CSV files from `data/processed/` next to the notebook.

## Folder structure

```text
app.py                       Streamlit entry point: navigation, logo, loads assets/style.css
pages/landing.py             Home page with the interactive illustration
pages/economic_growth.py ... One module per research page (labour_market, inflation,
                             policy_response, country_comparison, key_findings)
pages/home.py                Full report: all research pages on one page
pages/overview.py            About & methods
.streamlit/config.toml       Theme: colours, fonts, toolbar
assets/                      style.css (design system), logo.svg, logo_icon.svg
src/data/                    Data loading (loader.py, prepare.py), cleaning, merging, validation
src/analysis/                Shared calculations: economics.py (baselines, GDP index, tables),
                             correlation.py (Spearman, Bonferroni, within-year checks)
src/visualizations/          charts.py (country colours, chart builders), layout.py (navigation
                             registry, page headers, filters, insight and notes cards)
data/raw/                    Original downloaded data (kept unchanged)
data/processed/              Cleaned and merged datasets used by the app, plus the coverage audit
notebooks/                   Exploratory data analysis notebook (Colab)
tests/                       App smoke tests, data integrity checks, and findings checks
check_data_coverage.py       World Bank coverage audit
findings_summary.md          Authoritative findings for the dashboard and presentation
scrum.md                     Team ownership, backlog, and deadline checklist
AGENTS.md                    Instructions for future coding sessions
```

## Data handling and research decisions

Keep source data unchanged under `data/raw/` and document reproducible transformations in `data/processed/`. Record source URLs, access dates, transformations, units, and known gaps when data are added. Never treat missing values as zero or present placeholders as research results.

**Git and data:** `.gitignore` ignores the intermediate pipeline folders (`data/processed/<source>/`, `clean_stringency/`) but tracks the CSV files at the top of `data/processed/`, which the app reads. A fresh clone can therefore run the app without rebuilding the data.

**Sources:** World Bank World Development Indicators (NY.GDP.MKTP.KD.ZG, FP.CPI.TOTL.ZG, SL.UEM.TOTL.ZS; files last updated 2026-10-08); WHO COVID-19 cases and deaths via Our World in Data; Oxford COVID-19 Government Response Tracker (Blavatnik School of Government) via Our World in Data.

**Method choices to state in the presentation:** each country is compared with its own 2018–2019 average (two years only, so one unusual year, such as Rwanda's −0.3% inflation in 2018, shifts the baseline); the GDP "trend benchmark" extends 2018–2019 growth and is illustrative, not a counterfactual; correlations are exploratory, pooled over 21 country-years, and none survives a multiple-testing correction.
