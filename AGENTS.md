# Instructions for future coding sessions

- Preserve existing student work. Inspect files and this guidance before editing; avoid replacing files without a clear reason.
- Keep the project beginner-friendly and modular. Use Streamlit for the app, pandas for tabular data, and Plotly for agreed interactive charts.
- Do not make country, indicator, source, or causal research decisions for the team. Flag these for team agreement and describe evidence and limitations.
- Treat missing data as missing, never as zero. Distinguish an unavailable value from a failed request or unverified coverage.
- Keep raw source data unchanged in `data/raw/`; document reproducible cleaning and derived data in `data/processed/`. Avoid committing large downloads or secrets; preserve the small coverage audit.
- Keep Streamlit page content in `pages/`, reusable data and analysis code in `src/`, and shared visual assets in `assets/`.
- Use clear names, short functions, and comments that help students with basic Python knowledge.
- Do not present placeholder, generated, or fabricated values as research results. Label scaffolding clearly.
- Keep dependencies minimal. Do not add databases, containers, or deployment infrastructure unless the team asks.
- Update `README.md` and `scrum.md` when project setup or workflow changes materially.