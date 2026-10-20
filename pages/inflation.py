"""Research page 3: Inflation."""

import streamlit as st

from src.analysis.economics import recovery_table
from src.visualizations.charts import (
    country_bar_chart,
    country_line_chart,
    show_figure,
)
from src.visualizations.layout import (
    count_text,
    fmt,
    insight_card,
    load_data_or_stop,
    notes_card,
    page_header,
    require_countries,
    section_title,
    sidebar_filters,
)


def inflation_insights(econ, countries):
    n = len(countries)
    medians = econ.groupby("year")["inflation_pct"].median()
    effects = econ[econ["year"] == 2022].set_index("country")["inflation_effect_pp"].dropna()
    window = econ[econ["year"].between(2018, 2024)].dropna(subset=["inflation_pct"])
    items = []
    label = "Median inflation" if n > 1 else "Inflation"
    sentence = (
        f"{label} was <b>{fmt(medians.get(2020))}%</b> in 2020 and "
        f"<b>{fmt(medians.get(2022))}%</b> in 2022"
    )
    if medians.get(2022, 0) > medians.get(2020, 0) + 1:
        sentence += ": prices rose fastest after the 2020 output and jobs shock, not during it"
    items.append(sentence + ".")
    if len(effects) > 1:
        top = effects.sort_values(ascending=False).head(3)
        items.append(
            "Largest 2022 rises against own 2018–2019 average: "
            + ", ".join(f"<b>{c}</b> ({v:+.1f} pp)" for c, v in top.items())
            + "."
        )
    elif len(effects) == 1:
        items.append(
            f"2022 inflation was {effects.iloc[0]:+.1f} pp against the "
            "country's own 2018–2019 average."
        )
    if not window.empty:
        peak = window.loc[window["inflation_pct"].idxmax()]
        items.append(
            f"Highest annual rate, 2018–2024: <b>{peak['inflation_pct']:.1f}%</b> "
            f"({peak['country']}, {int(peak['year'])})."
        )
        always_low = [
            c for c, g in window.groupby("country") if (g["inflation_pct"] < 3).all()
        ]
        if always_low and n > 1:
            items.append(f"Below 3% in every year 2018–2024: {', '.join(always_low)}.")
    latest = econ[econ["year"] == 2024].dropna(subset=["inflation_pct"])
    if not latest.empty:
        items.append(
            f"In 2024, <b>{int((latest['inflation_pct'] < 3).sum())} of "
            f"{count_text(len(latest))}</b> had inflation below 3%."
        )
    return items


def render_inflation(data, countries, years):
    econ = data["economic"][data["economic"]["country"].isin(countries)]

    page_header(
        "inflation",
        "Annual consumer price inflation (World Bank) by country, inflation in "
        "2022 compared with each country's own 2018–2019 average, and how high "
        "inflation peaked before falling back.",
    )

    medians = econ.groupby("year")["inflation_pct"].median()
    window = econ.dropna(subset=["inflation_pct"])
    above5 = econ[(econ["year"] == 2022)]["inflation_pct"].dropna()
    word = "Median inflation" if len(countries) > 1 else "Inflation"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"{word}, 2020", f"{fmt(medians.get(2020))}%", border=True)
    k2.metric(
        f"{word}, 2022", f"{fmt(medians.get(2022))}%",
        delta=f"{fmt(medians.get(2022) - medians.get(2020), '{:+.1f}')} pp vs 2020",
        delta_color="inverse", border=True,
    )
    if not window.empty:
        peak = window.loc[window["inflation_pct"].idxmax()]
        k3.metric("Highest annual rate, 2018–24", f"{peak['inflation_pct']:.1f}%",
                  border=True)
        k3.caption(f"{peak['country']}, {int(peak['year'])}")
    k4.metric(
        "Above 5% in 2022", f"{int((above5 > 5).sum())} of {len(above5)}",
        help="Countries with consumer price inflation above 5% in 2022.",
        border=True,
    )

    left, right = st.columns([2.3, 1])
    with left:
        fig = country_line_chart(
            econ[econ["year"].between(*years)], "year", "inflation_pct",
            f"Consumer price inflation, {years[0]}–{years[1]}",
            "Inflation (% per year)",
            shade=years[0] <= 2021 and years[1] >= 2020, zero_line=True,
        )
        show_figure(fig, "inflation-line", height=440)
    with right:
        insight_card("Key insights", inflation_insights(econ, countries))

    section_title(
        "The 2022 price surge against each country's normal",
        "Left: 2022 inflation minus the 2018–2019 average. Right: peak and latest rates.",
    )
    left, right = st.columns([1, 1.25])
    with left:
        fig = country_bar_chart(
            econ[econ["year"] == 2022][["country", "inflation_effect_pp"]],
            "inflation_effect_pp",
            "2022 inflation minus 2018–2019 average",
            "Percentage points", unit=" pp",
        )
        show_figure(fig, "inflation-effect", height=380)
    with right:
        table = recovery_table(econ, "inflation_pct", countries)
        with st.container(border=True):
            st.markdown("**Inflation: before, peak, and latest (%)**")
            if table.empty:
                st.info("No inflation data for this selection.")
            else:
                st.dataframe(
                    table.style.format(
                        {"2019": "{:.1f}", "Peak 2020–24": "{:.1f}",
                         "Peak year": "{:.0f}", "2024": "{:.1f}"},
                        na_rep="—",
                    ),
                    hide_index=True, width="stretch",
                )

    notes_card([
        "Inflation is the annual change in consumer prices (World Bank FP.CPI.TOTL.ZG), "
        "an average over the year.",
        "A lower inflation rate means prices rose more slowly, not that they fell: "
        "price levels stayed higher after 2022.",
        "The 2018–2019 baseline is only two years. Rwanda's 2018 inflation was −0.3%, "
        "so its baseline is unusually low and its 2022 difference is large.",
        "2022 inflation also reflects energy and food price shocks and monetary policy, "
        "so these charts show timing, not the share caused by the pandemic.",
    ])


def show_inflation():
    data = load_data_or_stop()
    countries, years = sidebar_filters(data["countries"])
    require_countries(countries)
    render_inflation(data, countries, years)
