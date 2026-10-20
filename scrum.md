# Team Scrum Board

**Team:** Four students (names unassigned)  
**Presentation:** 20 minutes  
**Deadline:** October 21, 2026  
**App framework:** Streamlit (migrated from Dash)

## Ownership (assign names as a team)

| Role | Owner | Initial responsibility |
| --- | --- | --- |
| Project coordination and story | Unassigned | Coordinate milestones, agree on research scope, shape the presentation narrative |
| Economic data | Unassigned | Validate World Bank definitions and coverage; document selected economic measures |
| Pandemic data | Unassigned | Validate COVID-19 source, definitions, dates, and country comparability |
| App, charts, and integration | Unassigned | Maintain Streamlit pages, build reusable Plotly charts, integrate reviewed results |

Pair review major data transformations and claims across roles. Roles are a starting point and can be changed by the team.

## Prioritized backlog

| Priority | Item | Status | Acceptance note |
| --- | --- | --- | --- |
| P0 | Assign owners and agree final research scope | To do | Record countries, years, indicators, and pandemic measures |
| P0 | Review the existing economic coverage audit | Ready | Discuss missing values and any unverified requests without regenerating results unnecessarily |
| P0 | Validate COVID-19 source coverage and methodology | To do | Record source version, definitions, units, and missingness |
| P1 | Build documented download and cleaning pipeline | To do | Raw inputs preserved; transformations reproducible |
| P1 | Complete exploratory analysis and statistical summaries | To do | Methods and limitations documented; no unsupported causal claims |
| P1 | Build reviewed Plotly charts in Streamlit pages | To do | Charts use validated data and clearly labeled units and sources |
| P2 | Draft and rehearse the 20-minute presentation | To do | Clear story, balanced speaking roles, sources and limitations included |

## Progress

- [x] Created initial project structure and placeholder app.
- [x] Migrated app navigation and page content from Dash to Streamlit.
- [x] Preserved the existing World Bank coverage audit and audit script.
- [x] Updated setup instructions and future-session guidance for Streamlit.
- [x] Cleaned the 3 World Bank indicators (GDP growth, inflation, unemployment) into `data/processed/{gdp_growth,inflation,unemployment}/`, matching the 7-country format of the stringency and cases/deaths datasets.
- [x] Built `merged_dataset_by_month.csv` and `merged_dataset_by_year.csv` in `data/processed/`, limited to the 2020-2022 window every dataset covers (see `data/processed/merge_quality_report.md`).
- [x] Built the EDA notebook and the interactive Streamlit dashboard (overview and dashboard pages).
- [x] October 20 (visualisation, design, testing, and integration):
  - Added the missing `scipy` dependency; the app now starts after `pip install -r requirements.txt`.
  - Fixed country colours and markers on every chart (colour-blind-safe palette), a fixed light theme, and CSS readability tweaks.
  - Removed the misleading "strongest correlation" headline; added Bonferroni-adjusted p-values and within-year checks.
  - Added app smoke tests, processed-data integrity tests, and findings checks (`python -m unittest discover -s tests`).
  - Merged the two findings files into the single authoritative `findings_summary.md`.
  - Corrected the README setup and data-pipeline commands.
- [x] October 20 (design): multi-page dashboard with a Home page (virus-and-globe illustration and navigation cards) and six research pages (Economic Growth, Labour Market, Inflation, Pandemic & Policy Response, Country Comparisons, Key Findings); shared filters, editorial theme, shared analysis code in `src/analysis/`, and tests for every page.
- [x] Installed dependencies in the `covid-dashboard` Conda environment and smoke-tested the Streamlit app.
- [ ] Assign names and confirm ownership.
- [ ] Agree final countries, measures, and source choices (current dashboard: 7 countries, 2018–2024 economy, 2020–2022 pandemic).
- [ ] Team sign-off on the method caveats in `findings_summary.md` (2018–2019 baseline, trend benchmark, equal-weight impact ranking).

## Remaining work before October 21

- [ ] October 16: assign owners; review economic audit and agree on validation plan.
- [ ] October 17: validate pandemic source and decide final comparison set.
- [ ] October 18: complete reproducible analysis and chart drafts; peer review claims.
- [ ] October 19: integrate final charts and draft the presentation narrative.
- [ ] October 20: verify citations and limitations; rehearse the 20-minute presentation.
- [ ] October 21: deliver presentation and archive final code and data documentation.

These are suggested checkpoints based on the stated deadline; adjust them at the team check-in.