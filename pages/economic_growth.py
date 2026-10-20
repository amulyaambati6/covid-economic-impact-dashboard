"""Research page 1: Economic Growth."""

import plotly.express as px
import streamlit as st

from src.analysis.economics import gdp_index_paths
from src.visualizations.charts import (
    REFERENCE_LINE,
    country_bar_chart,
    country_line_chart,
    country_style,
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


def growth_insights(econ, index_df, final_df, countries):
    """Short, data-based statements for the selected countries."""
    n = len(countries)
    medians = econ.groupby("year")["gdp_growth_pct"].median()
    g2020 = econ[econ["year"] == 2020].set_index("country")["gdp_growth_pct"].dropna()
    effects = econ[econ["year"] == 2020].set_index("country")["gdp_effect_pp"].dropna()
    items = []

    label = "Median growth" if n > 1 else "Growth"
    items.append(
        f"{label} went from <b>{fmt(medians.get(2019))}%</b> in 2019 to "
        f"<b>{fmt(medians.get(2020))}%</b> in 2020, then "
        f"<b>{fmt(medians.get(2021))}%</b> in 2021."
    )
    if not g2020.empty:
        contracted = int((g2020 < 0).sum())
        grew = [c for c, v in g2020.items() if v >= 0]
        text = f"<b>{contracted} of {count_text(len(g2020))}</b> contracted in 2020"
        if grew and n > 1:
            text += f"; {', '.join(grew)} kept growing"
        items.append(text + ".")
    if len(effects) > 1:
        worst = effects.idxmin()
        items.append(
            f"Largest 2020 shortfall against its own 2018–2019 average: "
            f"<b>{worst}</b> ({effects[worst]:+.1f} pp)."
        )
    elif len(effects) == 1:
        items.append(
            f"2020 growth was {effects.iloc[0]:+.1f} pp against "
            "the country's own 2018–2019 average."
        )
    if not index_df.empty:
        actual = index_df[index_df["series"] == "Actual path"]
        above_2022 = actual[(actual["year"] == 2022) & (actual["index"] > 100)]
        items.append(
            f"By 2022, <b>{len(above_2022)} of {count_text(actual['country'].nunique())}</b> "
            "were larger than in 2019 (reconstructed index)."
        )
    if not final_df.empty:
        below = final_df[final_df["Difference from trend (%)"] < 0]
        text = (
            f"In 2024, <b>{len(below)} of {count_text(len(final_df))}</b> were below "
            "their 2018–2019 growth trend"
        )
        if len(final_df) > 1:
            lowest = final_df.loc[final_df["Difference from trend (%)"].idxmin()]
            text += (
                f"; furthest below: {lowest['Country']} "
                f"({lowest['Difference from trend (%)']:+.1f}%)"
            )
        items.append(text + ".")
    return items


def render_economic_growth(data, countries, years):
    econ = data["economic"][data["economic"]["country"].isin(countries)]

    page_header(
        "growth",
        "Annual real GDP growth from the World Bank for each country, compared "
        "with the country's own 2018–2019 average, and a reconstructed GDP level "
        "that shows how far each economy had recovered by 2024.",
    )

    # Headline figures use fixed reference years, whatever the year filter.
    medians = econ.groupby("year")["gdp_growth_pct"].median()
    g2020 = econ[econ["year"] == 2020]["gdp_growth_pct"].dropna()
    word = "Median GDP growth" if len(countries) > 1 else "GDP growth"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"{word}, 2019", f"{fmt(medians.get(2019))}%", border=True)
    k2.metric(
        f"{word}, 2020", f"{fmt(medians.get(2020))}%",
        delta=f"{medians.get(2020) - medians.get(2019):+.1f} pp vs 2019",
        border=True,
    )
    k3.metric(
        f"{word}, 2021", f"{fmt(medians.get(2021))}%",
        delta=f"{medians.get(2021) - medians.get(2020):+.1f} pp vs 2020",
        border=True,
    )
    k4.metric(
        "Contracted in 2020",
        f"{int((g2020 < 0).sum())} of {len(g2020)}",
        help="Countries with negative real GDP growth in 2020.",
        border=True,
    )

    index_df, final_df = gdp_index_paths(econ, countries)

    left, right = st.columns([2.3, 1])
    with left:
        shown = econ[econ["year"].between(*years)]
        fig = country_line_chart(
            shown, "year", "gdp_growth_pct",
            f"Annual real GDP growth, {years[0]}–{years[1]}",
            "GDP growth (% per year)", shade=years[0] <= 2021 and years[1] >= 2020,
            zero_line=True,
        )
        show_figure(fig, "growth-line", height=440)
    with right:
        insight_card("Key insights", growth_insights(econ, index_df, final_df, countries))

    section_title(
        "Against each country's own normal",
        "Bars compare 2020 growth with the country's 2018–2019 average; "
        "the right chart compares the 2024 GDP level with a simple pre-COVID trend.",
    )
    left, right = st.columns(2)
    with left:
        shortfall = econ[econ["year"] == 2020][["country", "gdp_effect_pp"]]
        fig = country_bar_chart(
            shortfall, "gdp_effect_pp",
            "2020 GDP growth minus 2018–2019 average",
            "Percentage points", unit=" pp",
        )
        show_figure(fig, "growth-shortfall", height=380)
    with right:
        gap = final_df.rename(
            columns={"Country": "country", "Difference from trend (%)": "gap"}
        ) if not final_df.empty else final_df
        fig = country_bar_chart(
            gap, "gap", "2024 GDP level vs pre-COVID trend benchmark",
            "Difference from benchmark (%)", unit="%",
        ) if not final_df.empty else None
        show_figure(fig, "growth-trend-gap", height=380,
                    empty_message="Needs complete 2018–2024 data.")

    section_title(
        "Recovery of the GDP level",
        "Each panel compounds the country's annual growth from 2019 = 100 "
        "(solid) and compares it with its 2018–2019 growth continued (dotted).",
    )
    if index_df.empty:
        show_figure(None, "growth-index",
                    empty_message="The index needs complete growth data for 2018–2024.")
    else:
        n_panels = index_df["country"].nunique()
        fig = px.line(
            index_df, x="year", y="index", color="country", line_dash="series",
            line_dash_map={"Actual path": "solid", "Pre-COVID trend benchmark": "dot"},
            facet_col="country", facet_col_wrap=min(4, n_panels),
            facet_row_spacing=0.16, markers=True,
            title="Reconstructed GDP index (2019 = 100): actual (solid) vs trend (dotted)",
            labels={"year": "Year", "index": "Index", "series": "Measure"},
            **country_style(markers=False),
        )
        fig.for_each_annotation(lambda a: a.update(text=f"<b>{a.text.split('=')[-1]}</b>"))
        fig.update_xaxes(dtick=2)
        fig.add_hline(y=100, **REFERENCE_LINE)
        fig.update_layout(showlegend=False)
        rows = -(-n_panels // 4)
        show_figure(fig, "growth-index", height=330 + 250 * (rows - 1))

    notes_card([
        "GDP growth is the annual percentage change in real GDP at constant prices "
        "(World Bank NY.GDP.MKTP.KD.ZG). Annual figures hide the depth of the "
        "quarterly fall in spring 2020.",
        "Differences from the 2018–2019 average are in percentage points, not the "
        "percentage change in the size of the economy. Two baseline years are a short "
        "normal: Rwanda's fast 2018–2019 growth (about 8.7% a year) makes its 2020 "
        "shortfall large even though France's economy shrank more.",
        "The index is rebuilt by compounding growth rates; it is not an observed GDP "
        "level. The trend benchmark is illustrative, not an estimate of GDP lost to COVID-19.",
        "Growth also reflects other events (for example energy prices in 2022), so the "
        "charts show timing and size, not cause.",
    ])


def show_economic_growth():
    data = load_data_or_stop()
    countries, years = sidebar_filters(data["countries"])
    require_countries(countries)
    render_economic_growth(data, countries, years)
