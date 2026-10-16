# COVID-19 and the Global Economy
## Project Documentation

- [Team Planning Document (Google Docs)](https://docs.google.com/document/d/1mCDpxkIXW9CLHjlG38D0ouK-Z_i__Tn6C99cpsMyHT8/edit?usp=sharing)

CentraleDigitalLab Data Storytelling university project exploring how COVID-19 affected the global economy. The presentation is planned for 20 minutes by a team of four, with a deadline of October 21, 2026.

## Research question

**How did COVID-19 impact the global economy?**

The initial study period is 2019–2023, subject to data validation. Candidate countries are the USA, India, France, China, Brazil, Germany, and Rwanda. Candidate economic indicators are GDP growth, unemployment, and inflation; pandemic measures are cases, deaths, and possibly government-response stringency. These are proposals, and the team must agree on final choices before drawing conclusions.

## Setup

Activate the existing Conda environment in Anaconda Prompt or the VS Code terminal:

```powershell
conda activate covid-dashboard
python -m pip install -r requirements.txt
```

## Run the app

From the project root:

```powershell
streamlit run app.py
```

Streamlit prints the local address to open in a browser. The app currently contains only project information and clearly marked chart placeholders; it does not display research findings.

## Check economic indicator coverage

The coverage script checks the three proposed World Bank indicators across the seven candidate countries for each year from 2019 through 2023. It requires internet access:

```powershell
python check_data_coverage.py
```

The script writes `data/processed/coverage_audit.csv`, one row per country, indicator, and year. The existing audit is preserved. Missing source values and request errors are marked separately; a request error means coverage is unverified, not proven missing. Review the audit and source metadata as a team before making research decisions.

World Bank Indicators API documentation: <https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation>
Our World in Data COVID-19 data documentation: <https://github.com/owid/covid-19-data/tree/master/public/data>

## Clean and merge the data

Each raw source has its own cleaning script in `src/data/`, run from the project root. All of them keep the same 7 candidate countries (USA, India, France, China, Brazil, Germany, Rwanda) and write a `quality_report.md` next to their output.

```powershell
python src/data/clean_stringency.py data/raw/<stringency file> --out clean_stringency
python src/data/clean_deaths_cases.py data/raw/daily_cases_deaths_per_million.csv --out data/processed/cases_deaths
python src/data/clean_worldbank_indicators.py
```

`clean_worldbank_indicators.py` cleans the three World Bank downloads (`data/raw/world_bank_gdp_growth.xls`, `world_bank_inflation.xls`, `world_bank_unemployment.xls`) in one run, keeping 2018-2024, and writes one annual table per indicator under `data/processed/gdp_growth/`, `data/processed/inflation/`, and `data/processed/unemployment/`. Reading `.xls` needs the `xlrd` package (in `requirements.txt`).

Once all five datasets above exist, build the two combined tables used for analysis:

```powershell
python src/data/merge_datasets.py
```

This writes `data/processed/merged_dataset_by_month.csv` and `merged_dataset_by_year.csv` (plus matching `.xlsx` files and `merge_quality_report.md`). Stringency and cases/deaths are published monthly; GDP growth, inflation, and unemployment are only published yearly by the World Bank, so the by-month table repeats each year's economic figures across its 12 months, while the by-year table sums or averages the monthly figures up to a year. Both tables are limited to the period every input dataset covers, currently **2020-2022** (set by the stringency index, the shortest-covered input) — see `merge_quality_report.md` for the exact bounds found on the last run. This 3-year window is the only period with every variable available at once; it is a data-coverage fact, not a team decision about the final study period.

## Tests

Run the data helper checks from the project root:

```powershell
python -m unittest discover -s tests
```

## Folder structure

```text
app.py                       Streamlit entry point and sidebar navigation
pages/                       Streamlit page content modules
assets/style.css             Retained starter styles (not loaded by Streamlit automatically)
src/data/                    Download, validation, and cleaning helpers
src/analysis/                Exploratory and statistical summaries
src/visualizations/           Reusable Plotly chart functions
data/raw/                    Original downloaded data (ignored by Git)
data/processed/               Cleaned per-source data, merged datasets, and coverage audit (currently ignored by Git except coverage_audit.csv -- see note below)
tests/                       Basic data pipeline checks
check_data_coverage.py       World Bank coverage audit
scrum.md                      Team ownership, backlog, and deadline checklist
AGENTS.md                     Instructions for future coding sessions
```

## Data handling and research decisions

Keep source data unchanged under `data/raw/` and document reproducible transformations in `data/processed/`. Large downloads are ignored by Git; the small `coverage_audit.csv` is explicitly kept. Record source URLs, access dates, transformations, units, and known gaps when data are added. Never treat missing values as zero or present placeholders as research results.

**Note for the team:** `.gitignore` currently ignores everything under `data/processed/` except `coverage_audit.csv`, so the cleaned per-indicator tables and the two merged datasets stay local until the team decides whether to track them. They are all small CSVs produced deterministically by the scripts above (not large downloads), so committing them is reasonable if the team wants reviewers and the app to see them without re-running every script; agree on this before relying on their presence in a fresh clone.

The team still needs to agree on final countries, pandemic measures, indicator definitions, and whether the selected sources provide suitable coverage for the story. The project scaffold does not make those research decisions.