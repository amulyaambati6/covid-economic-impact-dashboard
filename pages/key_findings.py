"""Research page 6: Key Findings (all seven countries, computed live)."""

from pathlib import Path

import streamlit as st

from src.analysis.correlation import correlation_tables, spearman_or_nan
from src.analysis.economics import (
    gdp_index_paths,
    recovery_table,
    unemployment_change_2019_2020,
)
from src.visualizations.layout import (
    PAGE_BY_KEY,
    html_block,
    icon,
    load_data_or_stop,
    notes_card,
    page_header,
    section_title,
)

FINDINGS_FILE = Path(__file__).resolve().parents[1] / "findings_summary.md"


def compute_findings(data):
    """Return the headline statements per theme, each built from the data."""
    econ, ann = data["economic"], data["annual"]
    countries = data["countries"]
    n = len(countries)
    med = econ.groupby("year")[["gdp_growth_pct", "unemployment_pct", "inflation_pct"]].median()
    g2020 = econ[econ["year"] == 2020].set_index("country")
    shortfall = g2020["gdp_effect_pp"].sort_values().head(3)
    grew = g2020[g2020["gdp_growth_pct"] >= 0].index.tolist()

    change = unemployment_change_2019_2020(econ)
    top_u = change.idxmax()
    u_table = recovery_table(econ, "unemployment_pct", countries)
    late = u_table[u_table["Peak year"] > 2020]
    back = u_table[u_table["Back to 2019 level by 2024?"] == "Yes"]
    late_peaks = [f"{row['Country']} ({int(row['Peak year'])})" for _, row in late.iterrows()]

    infl = econ.dropna(subset=["inflation_pct"])
    peak = infl.loc[infl["inflation_pct"].idxmax()]
    low = [c for c, g in infl.groupby("country") if (g["inflation_pct"] < 3).all()]
    i2022 = econ[econ["year"] == 2022].set_index("country")["inflation_effect_pp"]
    top_i = i2022.sort_values(ascending=False).head(3)

    deaths = ann.groupby("country")["new_deaths_per_million"].sum().sort_values()
    sti = ann.pivot_table(index="country", columns="year", values="sti_weighted")
    rose = [c for c in sti.index if sti.loc[c, 2022] > sti.loc[c, 2020]]

    d2020 = ann[ann["year"] == 2020].set_index("country")["new_deaths_per_million"]
    rho_deaths, _, n_deaths = spearman_or_nan(d2020, g2020["gdp_effect_pp"])
    pooled, _, _ = correlation_tables(ann, econ)
    n_raw = int((pooled["p-value"] < 0.05).sum())
    n_adj = int((pooled["Bonferroni-adjusted p"] < 0.05).sum())

    index_df, final = gdp_index_paths(econ, countries)
    actual = index_df[index_df["series"] == "Actual path"]
    above_2022 = actual[(actual["year"] == 2022) & (actual["index"] > 100)]
    below_2021 = actual[(actual["year"] == 2021) & (actual["index"] < 100)]["country"].tolist()
    below_trend = final[final["Difference from trend (%)"] < 0]
    worst_trend = final.loc[final["Difference from trend (%)"].idxmin()]
    best_trend = final.loc[final["Difference from trend (%)"].idxmax()]

    def names(items):
        items = list(items)
        return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]

    return {
        "growth": [
            f"Median GDP growth fell from <b>{med.loc[2019, 'gdp_growth_pct']:.1f}%</b> (2019) "
            f"to <b>{med.loc[2020, 'gdp_growth_pct']:.1f}%</b> (2020) and rebounded to "
            f"<b>{med.loc[2021, 'gdp_growth_pct']:.1f}%</b> (2021).",
            f"<b>{n - len(grew)} of {n}</b> economies contracted in 2020"
            + (f"; {names(grew)} kept growing." if grew else "."),
            "Largest 2020 shortfalls against their own 2018–2019 average: "
            + ", ".join(f"{c} ({v:+.1f} pp)" for c, v in shortfall.items()) + ".",
        ],
        "labour": [
            f"Unemployment rose most from 2019 to 2020 in <b>{top_u}</b> "
            f"({change[top_u]:+.1f} pp).",
            f"Median unemployment: <b>{med.loc[2019, 'unemployment_pct']:.1f}%</b> (2019), "
            f"<b>{med.loc[2020, 'unemployment_pct']:.1f}%</b> (2020), "
            f"<b>{med.loc[2021, 'unemployment_pct']:.1f}%</b> (2021).",
            (f"Later peaks: {names(late_peaks)}. " if late_peaks else "")
            + f"{len(back)} of {n} returned to their 2019 rate by 2024.",
        ],
        "inflation": [
            f"Median inflation was <b>{med.loc[2020, 'inflation_pct']:.1f}%</b> in 2020 and "
            f"<b>{med.loc[2022, 'inflation_pct']:.1f}%</b> in 2022: prices rose fastest "
            "after the output and jobs shock.",
            "Largest 2022 rises against own normal: "
            + ", ".join(f"{c} ({v:+.1f} pp)" for c, v in top_i.items()) + ".",
            f"Highest annual rate: <b>{peak['inflation_pct']:.1f}%</b> ({peak['country']}, "
            f"{int(peak['year'])})" + (f"; {names(low)} stayed below 3% throughout." if low else "."),
        ],
        "policy": [
            f"Highest reported deaths, 2020–22: {deaths.index[-1]} "
            f"(<b>{deaths.iloc[-1]:,.0f}</b> per million) and {deaths.index[-2]} "
            f"({deaths.iloc[-2]:,.0f}); lowest: {deaths.index[0]} ({deaths.iloc[0]:,.0f}).",
            f"Restrictions were less strict in 2022 than in 2020 in <b>{n - len(rose)} of {n}</b>"
            + (f"; stricter only in {names(rose)}." if rose else "."),
            f"{n_raw} of {len(pooled)} pooled correlation tests had p < 0.05 and "
            f"<b>{n_adj}</b> survived a multiple-testing correction.",
        ],
        "comparison": [
            f"In 2020 the GDP shortfall did not follow reported deaths: rank correlation "
            f"<b>ρ = {rho_deaths:+.2f}</b> (n = {n_deaths}).",
            f"{shortfall.index[0]} and {shortfall.index[1]} had the largest shortfalls while "
            f"reporting {d2020[shortfall.index[0]]:,.0f} and {d2020[shortfall.index[1]]:,.0f} "
            "deaths per million in 2020.",
            "Impacts differ widely, so a seven-country median hides very different experiences.",
        ],
        "recovery": [
            f"<b>{len(above_2022)} of {n}</b> economies were larger than in 2019 by 2022"
            + (f"; {names(below_2021)} were still below it in 2021." if below_2021 else "."),
            f"In 2024, <b>{len(below_trend)} of {n}</b> were below their 2018–2019 growth "
            f"trend; furthest below: {worst_trend['Country']} "
            f"({worst_trend['Difference from trend (%)']:+.1f}%).",
            f"Highest relative to trend: {best_trend['Country']} "
            f"({best_trend['Difference from trend (%)']:+.1f}%), helped by a slow 2018–2019 benchmark.",
        ],
    }


CARD_TITLES = {
    "growth": "Economic growth",
    "labour": "Labour market",
    "inflation": "Inflation",
    "policy": "Pandemic & policy",
    "comparison": "Country comparisons",
    "recovery": "Recovery by 2024",
}


def render_key_findings(data):
    page_header(
        "findings",
        "Headline results for all seven countries, calculated live from the project "
        "datasets (filters do not apply here), followed by our assessment of what the "
        "data can and cannot show.",
    )

    findings = compute_findings(data)
    cards = []
    for key, items in findings.items():
        link_page = PAGE_BY_KEY["growth" if key == "recovery" else key]
        bullets = "".join(f"<li>{item}</li>" for item in items if item)
        cards.append(
            f'<article class="finding-card">'
            f'<h4>{icon(link_page["icon"], 22)} {CARD_TITLES[key]}</h4>'
            f"<ul>{bullets}</ul>"
            f'<a class="finding-card__link" href="{link_page["url_path"]}" target="_self">'
            f'Explore {link_page["title"]} <span aria-hidden="true">→</span></a>'
            f"</article>"
        )
    html_block(f'<div class="finding-grid">{"".join(cards)}</div>')

    section_title(
        "Are the data sufficient to measure the pandemic's economic impact?",
        "Draft assessment for team review, as the brief asks for a justified answer.",
    )
    html_block("""
    <div class="verdict">
    <p class="verdict__answer">Partly.</p>
    <div class="verdict__cols">
    <div><h5>Sufficient to show</h5><ul>
    <li>When and how much growth, unemployment and inflation changed in seven countries.</li>
    <li>How each country compared with its own pre-pandemic years.</li>
    <li>When reported cases, deaths and restrictions rose and fell.</li>
    </ul></div>
    <div><h5>Not sufficient to show</h5><ul>
    <li>How much of the change COVID-19 <i>caused</i>: there is no counterfactual and
    other shocks overlapped (for example 2022 energy and food prices).</li>
    <li>Short-term dynamics: economic data are annual and the baseline is two years.</li>
    <li>A global picture: seven countries are a purposive sample, and reported health
    data differ in quality between countries.</li>
    </ul></div>
    </div>
    </div>
    """)

    notes_card([
        "All statements describe the seven countries studied, not the world economy.",
        "Economic differences compare each country with its own 2018–2019 average; the "
        "trend benchmark extends that growth and is illustrative.",
        "Correlations are exploratory; none survives a multiple-testing correction.",
        "The full write-up, including the EDA notebook's country ranking, is in "
        "findings_summary.md.",
    ], title="Read these findings with care")

    if FINDINGS_FILE.exists():
        st.download_button(
            "Download the findings summary (Markdown)",
            data=FINDINGS_FILE.read_text(encoding="utf-8"),
            file_name="findings_summary.md",
            mime="text/markdown",
            icon=":material/download:",
        )


def show_key_findings():
    data = load_data_or_stop()
    st.sidebar.caption("Key findings always cover all seven countries.")
    render_key_findings(data)
