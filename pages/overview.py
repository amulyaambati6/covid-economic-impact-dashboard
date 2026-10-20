"""About & methods: scope, sources, definitions, and how the data were built."""

import streamlit as st

from src.visualizations.layout import html_block, icon, notes_card


SOURCES = [
    ("GDP growth (annual %)", "World Bank WDI, NY.GDP.MKTP.KD.ZG", "2018–2024", "Annual"),
    ("Unemployment (% of labour force)", "World Bank WDI, SL.UEM.TOTL.ZS (modelled ILO)", "2018–2024", "Annual"),
    ("Inflation, consumer prices (annual %)", "World Bank WDI, FP.CPI.TOTL.ZG", "2018–2024", "Annual"),
    ("New cases and deaths per million", "WHO via Our World in Data", "2020–2022", "Daily, summed to months"),
    ("Government stringency index (0–100)", "Oxford COVID-19 Government Response Tracker via Our World in Data", "2020–2022", "Daily, averaged to months"),
]


def show_overview():
    html_block(f"""
    <header class="page-head">
    <div class="page-head__text">
    <p class="eyebrow">Reference</p>
    <h1 class="page-head__title">About &amp; methods</h1>
    <p class="page-head__question">How were the data collected, prepared, and compared?</p>
    <p class="page-head__lede">A CentraleDigitalLab Data Storytelling project comparing seven
    countries: Brazil, China, France, Germany, India, Rwanda, and the United States.</p>
    </div>
    <div class="page-head__icon">{icon('about', 44)}</div>
    </header>
    """)

    rows = "".join(
        f"<tr><td>{measure}</td><td>{source}</td><td>{years}</td><td>{freq}</td></tr>"
        for measure, source, years, freq in SOURCES
    )
    html_block(f"""
    <div class="section-title"><h3>Data sources</h3>
    <p class="section-sub">World Bank files last updated 2026-10-08; raw downloads are kept unchanged in data/raw/.</p></div>
    <table class="source-table">
    <thead><tr><th>Measure</th><th>Source</th><th>Years used</th><th>Frequency</th></tr></thead>
    <tbody>{rows}</tbody>
    </table>
    """)

    html_block(f"""
    <div class="section-title"><h3>Methods in brief</h3></div>
    <div class="explainer">
    <div class="explainer__item"><h4>{icon('comparison', 20)} Own-normal comparison</h4>
    <p>Each economic indicator is compared with the country's average for 2018–2019.
    The difference is in percentage points (pp). Both baseline years are required.</p></div>
    <div class="explainer__item"><h4>{icon('growth', 20)} GDP index and trend</h4>
    <p>Annual real growth is compounded from 2019 = 100. The benchmark continues the
    2018–2019 average growth rate; it is illustrative, not a counterfactual.</p></div>
    <div class="explainer__item"><h4>{icon('policy', 20)} Monthly to yearly</h4>
    <p>Daily cases and deaths are summed into months and years; the stringency index
    is averaged. Months with fewer than 15 observed days are left missing, never zero.</p></div>
    <div class="explainer__item"><h4>{icon('findings', 20)} Exploratory statistics</h4>
    <p>Spearman rank correlations on country-years, shown with Bonferroni-adjusted
    p-values and the same correlations within each year.</p></div>
    </div>
    """)

    html_block(f"""
    <div class="section-title"><h3>How to read the dashboard</h3></div>
    <ul class="plain-list">
    <li>Each country keeps the <b>same colour and marker</b> on every chart.</li>
    <li>The <b>sidebar filters</b> (countries, years) apply to every research page and are
    kept when you move between pages. Headline figures use fixed reference years.</li>
    <li>The grey band on annual charts marks <b>2020–2021</b>, the main pandemic shock.</li>
    <li>The data are reproducible: see README.md for the cleaning and merge commands, and
    run <code>python -m unittest discover -s tests</code> to check the data and findings.</li>
    </ul>
    """)

    notes_card([
        "Seven countries are a purposive sample; results describe them, not the world economy.",
        "Reported cases and deaths depend on testing and registration rules.",
        "Annual economic data hide short-term swings within a year.",
        "Correlations do not establish cause; other shocks overlapped with the pandemic.",
    ], title="Main limitations")
