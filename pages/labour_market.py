"""Research page 2: Labour Market."""

import pandas as pd
import streamlit as st

from src.analysis.economics import recovery_table, unemployment_change_2019_2020
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


def labour_insights(econ, change, table, countries):
    n = len(countries)
    medians = econ.groupby("year")["unemployment_pct"].median()
    effects = econ[econ["year"] == 2020].set_index("country")["unemployment_effect_pp"]
    items = []
    label = "Median unemployment" if n > 1 else "Unemployment"
    items.append(
        f"{label} was <b>{fmt(medians.get(2019))}%</b> in 2019, "
        f"<b>{fmt(medians.get(2020))}%</b> in 2020 and "
        f"<b>{fmt(medians.get(2021))}%</b> in 2021."
    )
    if not change.empty:
        top = change.idxmax()
        if n == 1:
            items.append(
                f"From 2019 to 2020 unemployment changed by <b>{change[top]:+.1f} pp</b> "
                f"({fmt(effects.get(top), '{:+.1f}')} pp against its 2018–2019 average)."
            )
        elif change.max() > 0:
            items.append(
                f"Largest rise, 2019 to 2020: <b>{top}</b> ({change[top]:+.1f} pp; "
                f"{fmt(effects.get(top), '{:+.1f}')} pp against its 2018–2019 average)."
            )
        fell = [c for c, v in change.items() if v < 0]
        if fell and n > 1:
            items.append(f"Unemployment fell in 2020 in {', '.join(fell)}.")
    if not table.empty:
        late = table[table["Peak year"].fillna(0) > 2020]
        if not late.empty and n > 1:
            items.append(
                "Peak came after 2020 in "
                + ", ".join(f"{r.Country} ({int(r['Peak year'])})" for _, r in late.iterrows())
                + "."
            )
        back = table[table["Back to 2019 level by 2024?"] == "Yes"]
        items.append(
            f"<b>{len(back)} of {count_text(len(table))}</b> returned to their 2019 "
            "rate at some point from 2021 to 2024."
        )
    return items


def render_labour_market(data, countries, years):
    econ = data["economic"][data["economic"]["country"].isin(countries)]

    page_header(
        "labour",
        "The unemployment rate (share of the labour force without work, World Bank "
        "modelled ILO estimate) by year, the change from 2019 to 2020, and whether "
        "each country returned to its pre-pandemic rate.",
    )

    medians = econ.groupby("year")["unemployment_pct"].median()
    change = unemployment_change_2019_2020(econ)
    word = "Median unemployment" if len(countries) > 1 else "Unemployment"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"{word}, 2019", f"{fmt(medians.get(2019))}%", border=True)
    k2.metric(
        f"{word}, 2020", f"{fmt(medians.get(2020))}%",
        delta=f"{fmt(medians.get(2020) - medians.get(2019), '{:+.1f}')} pp vs 2019",
        delta_color="inverse", border=True,
    )
    if not change.empty and change.max() > 0:
        k3.metric(
            "Biggest rise, 2019 to 2020", f"{change.max():+.1f} pp",
            help="Change in the unemployment rate from 2019 to 2020.",
            border=True,
        )
        k3.caption(change.idxmax())
    else:
        k3.metric("Unemployment change, 2019 to 2020",
                  fmt(change.max() if not change.empty else None, "{:+.1f} pp"),
                  border=True)
    k4.metric(
        f"{word}, 2024", f"{fmt(medians.get(2024))}%",
        delta=f"{fmt(medians.get(2024) - medians.get(2019), '{:+.1f}')} pp vs 2019",
        delta_color="inverse", border=True,
    )

    table = recovery_table(econ, "unemployment_pct", countries)

    left, right = st.columns([2.3, 1])
    with left:
        fig = country_line_chart(
            econ[econ["year"].between(*years)], "year", "unemployment_pct",
            f"Unemployment rate, {years[0]}–{years[1]}",
            "Unemployment (% of labour force)",
            shade=years[0] <= 2021 and years[1] >= 2020,
        )
        show_figure(fig, "labour-line", height=440)
    with right:
        insight_card("Key insights", labour_insights(econ, change, table, countries))

    section_title(
        "The 2020 shock and the recovery",
        "Left: change from 2019 to 2020. Right: where each country ended up.",
    )
    left, right = st.columns([1, 1.25])
    with left:
        fig = country_bar_chart(
            pd.DataFrame({"country": change.index, "change": change.values}),
            "change", "Change in unemployment rate, 2019 to 2020",
            "Percentage points", unit=" pp",
        )
        show_figure(fig, "labour-change", height=380)
    with right:
        with st.container(border=True):
            st.markdown("**Unemployment rate: before, peak, and latest (%)**")
            if table.empty:
                st.info("No unemployment data for this selection.")
            else:
                st.dataframe(
                    table.style.format(
                        {"2019": "{:.1f}", "Peak 2020–24": "{:.1f}",
                         "Peak year": "{:.0f}", "2024": "{:.1f}"},
                        na_rep="—",
                    ),
                    hide_index=True, width="stretch",
                )
                st.caption(
                    "'Back to 2019 level' means at or below the 2019 rate in at "
                    "least one year from 2021 to 2024."
                )

    notes_card([
        "Unemployment is the World Bank's modelled ILO estimate (SL.UEM.TOTL.ZS), "
        "which makes countries comparable but is partly model-based.",
        "Annual averages smooth out short spikes within 2020, so the monthly peak "
        "of the first lockdowns is not visible here.",
        "In economies with large informal sectors (for example India and Rwanda) "
        "the unemployment rate captures job losses less fully; people may lose income "
        "without being counted as unemployed.",
        "Job-retention schemes (for example in France and Germany) kept workers "
        "employed, so low unemployment does not mean an unaffected labour market.",
    ])


def show_labour_market():
    data = load_data_or_stop()
    countries, years = sidebar_filters(data["countries"])
    require_countries(countries)
    render_labour_market(data, countries, years)
