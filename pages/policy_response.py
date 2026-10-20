"""Research page 4: Pandemic & Policy Response."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.correlation import correlation_tables, within_year_consistent
from src.visualizations.charts import (
    REFERENCE_LINE,
    country_bar_chart,
    country_line_chart,
    country_style,
    show_figure,
)
from src.visualizations.layout import (
    count_text,
    html_block,
    load_data_or_stop,
    notes_card,
    page_header,
    require_countries,
    section_title,
    sidebar_filters,
)

# Single-hue ramp (ivory to deep rose) for the stringency heatmap.
STRINGENCY_SCALE = ["#FBF3EE", "#F2CFCB", "#DE9A9F", "#B8586E", "#7A2945"]


def pandemic_kpis(mon, ann):
    totals = ann.groupby("country")["new_deaths_per_million"].sum(min_count=1).dropna()
    k1, k2, k3, k4 = st.columns(4)
    if not totals.empty:
        k1.metric("Highest reported deaths per million, 2020–22",
                  f"{totals.max():,.0f}", border=True)
        k1.caption(totals.idxmax())
        k2.metric("Lowest reported deaths per million, 2020–22",
                  f"{totals.min():,.0f}", border=True)
        k2.caption(f"{totals.idxmin()}: low reported figures may reflect reporting.")
    strict = mon.dropna(subset=["sti_weighted"])
    if not strict.empty:
        peak = strict.loc[strict["sti_weighted"].idxmax()]
        k3.metric("Strictest month (stringency 0–100)", f"{peak['sti_weighted']:.1f}",
                  border=True)
        k3.caption(f"{peak['country']}, {peak['month']:%B %Y}")
    gap = mon.assign(g=mon["sti_nonvaccinated"] - mon["sti_vaccinated"])
    differentiated = gap[gap["g"] > 0.05]["country"].nunique()
    k4.metric(
        "Rules differed by vaccination status",
        f"{differentiated} of {mon['country'].nunique()}",
        help="Countries where the non-vaccinated index was ever higher than "
        "the vaccinated index.",
        border=True,
    )


def cases_and_deaths(mon, ann):
    left, right = st.columns([1.2, 1])
    choice = left.radio(
        "Health indicator", ["New cases per million", "New deaths per million"],
        horizontal=True, key="policy_health_indicator",
    )
    scale = right.radio(
        "Chart scale",
        ["Logarithmic (all countries readable)", "Linear (true proportions)",
         "One panel per country"],
        horizontal=True, key="health_scale",
        help="Values differ by several orders of magnitude between countries, so "
        "on a linear scale a few countries dominate.",
    )
    column = "new_cases_per_million" if "cases" in choice else "new_deaths_per_million"
    word = "cases" if "cases" in choice else "deaths"
    plot = mon.dropna(subset=[column]).sort_values(["country", "month"])
    hidden = 0
    if scale.startswith("Logarithmic"):
        # A log axis cannot show zero; count the months that are left out.
        hidden = int((plot[column] <= 0).sum())
        plot = plot[plot[column] > 0]

    y_label = f"New {word} per million (monthly total)"
    title = f"Reported new COVID-19 {word} per million people, monthly totals"
    if plot.empty:
        fig = None
    elif scale == "One panel per country":
        fig = px.line(
            plot, x="month", y=column, color="country", facet_col="country",
            facet_col_wrap=4, facet_row_spacing=0.14, title=title,
            labels={"month": "", column: "", "country": "Country"},
            **country_style(markers=False),
        )
        fig.update_yaxes(matches=None, showticklabels=True)
        fig.for_each_annotation(lambda a: a.update(text=f"<b>{a.text.split('=')[-1]}</b>"))
        fig.update_layout(showlegend=False)
    else:
        fig = country_line_chart(
            plot, "month", column, title, y_label, markers=False,
            log_y=scale.startswith("Logarithmic"),
        )
        if scale.startswith("Logarithmic"):
            fig.update_yaxes(title_text=f"{y_label}, log scale")
    show_figure(fig, "policy-health", height=600 if scale == "One panel per country" else 470)

    notes = []
    if scale == "One panel per country":
        notes.append("Each panel has its own vertical scale: compare the timing of waves, not heights.")
    if hidden:
        notes.append(
            f"{hidden} country-month(s) with zero reported {word} cannot be drawn on a "
            "log scale and are not shown. Each step on the log axis is ten times the one below."
        )
    for note in notes:
        st.caption(note)

    totals = ann.groupby("country")[column].sum(min_count=1).reset_index()
    fig = country_bar_chart(
        totals, column, f"Total reported {word} per million, 2020–2022",
        f"{word.capitalize()} per million", text_format=",.0f", zero_line=False,
    )
    show_figure(fig, "policy-health-total", height=360)


def stringency(mon, ann):
    view = st.radio("View", ["Lines", "Heatmap (month by country)"],
                    horizontal=True, key="policy_stringency_view")
    plot = mon.dropna(subset=["sti_weighted"])
    if view == "Lines":
        fig = country_line_chart(
            plot, "month", "sti_weighted",
            "Government stringency index, monthly average, 2020–2022",
            "Stringency index (0–100)", markers=False,
        )
        if fig is not None:
            fig.update_yaxes(range=[0, 100])
    elif plot.empty:
        fig = None
    else:
        grid = plot.pivot_table(index="country", columns="month", values="sti_weighted")
        grid.columns = [c.strftime("%b %Y") for c in grid.columns]
        fig = px.imshow(
            grid, aspect="auto", zmin=0, zmax=100,
            color_continuous_scale=STRINGENCY_SCALE,
            labels={"color": "Stringency", "x": "", "y": ""},
            title="Government stringency index by month (darker = stricter)",
        )
        fig.update_xaxes(tickangle=-45, nticks=12)
    show_figure(fig, "policy-stringency", height=430)

    by_year = ann.pivot_table(index="country", columns="year", values="sti_weighted")
    if {2020, 2022}.issubset(by_year.columns):
        rose = [c for c in by_year.index if by_year.loc[c, 2022] > by_year.loc[c, 2020]]
        fell = len(by_year) - len(rose)
        text = (
            f"Average stringency was lower in 2022 than in 2020 in "
            f"<b>{fell} of {count_text(len(by_year))}</b>"
        )
        if rose:
            text += f"; it rose in {', '.join(rose)}"
        html_block(f'<p class="inline-insight">{text}.</p>')


def vaccination_gap(mon):
    gap = mon.assign(
        stringency_gap=mon["sti_nonvaccinated"] - mon["sti_vaccinated"]
    ).dropna(subset=["stringency_gap"])
    fig = country_line_chart(
        gap, "month", "stringency_gap",
        "Stricter rules for non-vaccinated people (non-vaccinated minus vaccinated index)",
        "Difference (index points)", markers=False, zero_line=True,
    )
    show_figure(fig, "policy-gap", height=420)
    st.caption(
        "Zero means the same rules applied to everyone. Positive values mean "
        "non-vaccinated people faced stricter rules."
    )


def links_with_economy(ann, econ):
    pooled, within, years = correlation_tables(ann, econ)
    if pooled.empty:
        st.warning(
            "There are not enough complete, varying observations to calculate "
            "the correlations for this selection."
        )
        return

    n_tests = len(pooled)
    n_raw = int((pooled["p-value"] < 0.05).sum())
    n_adjusted = int((pooled["Bonferroni-adjusted p"] < 0.05).sum())

    html_block(
        f'<div class="callout"><b>How to read this:</b> Spearman correlation checks '
        f"whether two measures rise and fall together in rank across country-years "
        f"(2020–2022). <b>{n_raw} of {n_tests}</b> tests have an unadjusted p-value "
        f"below 0.05 and <b>{n_adjusted}</b> remain below 0.05 after the Bonferroni "
        f"correction for running {n_tests} tests. Correlation does not show cause.</div>"
    )

    with st.container(border=True):
        st.dataframe(
            pooled.style.format({
                "Spearman rho": "{:+.2f}", "p-value": "{:.3f}",
                "Bonferroni-adjusted p": "{:.3f}",
            }),
            hide_index=True, width="stretch",
        )

    # Explain any pair that looks notable before correction.
    for _, row in pooled[pooled["p-value"] < 0.05].iterrows():
        match = within[
            (within["Health or policy indicator"] == row["Health or policy indicator"])
            & (within["Economic outcome"] == row["Economic outcome"])
        ].iloc[0]
        yearly = [f"{match[str(y)]:+.2f} in {y}" for y in years if pd.notna(match[str(y)])]
        if not yearly:
            continue
        if within_year_consistent(match, row["Spearman rho"], years):
            ending = ("The direction is the same in every year, but each single-year "
                      "sample is very small.")
        else:
            ending = ("The direction is not consistent within years, so the pooled value "
                      "mostly reflects differences between years (for example, restrictions "
                      "eased in 2022 while inflation peaked) rather than a stable link "
                      "between countries.")
        st.info(
            f"**{row['Health or policy indicator']} vs {row['Economic outcome']}:** "
            f"pooled ρ = {row['Spearman rho']:+.2f} (n = {int(row['Observations'])}), but "
            f"within single years ρ = {', '.join(yearly)}. {ending}"
        )

    with st.expander("Same correlations calculated within each single year"):
        st.dataframe(
            within.style.format(
                {c: "{:+.2f}" for c in within.columns
                 if c not in ("Health or policy indicator", "Economic outcome")},
                na_rep="—",
            ),
            hide_index=True, width="stretch",
        )
        st.caption(
            "Each year has at most one observation per selected country (n ≤ 7), so "
            "single-year values are very uncertain. They only check whether pooled "
            "results hold within years."
        )


def render_policy_response(data, countries, years):
    mon = data["monthly"][data["monthly"]["country"].isin(countries)]
    mon = mon[mon["year"].between(*years)]
    ann = data["annual"][data["annual"]["country"].isin(countries)]
    econ = data["economic"][data["economic"]["country"].isin(countries)]

    page_header(
        "policy",
        "Reported COVID-19 cases and deaths (WHO), the Oxford government stringency "
        "index, and exploratory tests of whether pandemic severity or strictness moved "
        "with economic outcomes. Pandemic data cover 2020–2022.",
    )

    if mon.empty:
        st.info(
            "Pandemic data cover 2020–2022 only. Widen the year range in the sidebar "
            "to include those years."
        )
        return

    pandemic_kpis(mon, ann)
    tabs = st.tabs(["Cases & deaths", "Government stringency",
                    "Rules by vaccination status", "Links with the economy"])
    with tabs[0]:
        cases_and_deaths(mon, ann)
    with tabs[1]:
        stringency(mon, ann)
    with tabs[2]:
        vaccination_gap(mon)
    with tabs[3]:
        section_title(
            "Did severity or strictness track economic change?",
            "Uses all 2020–2022 country-years for the selected countries.",
        )
        links_with_economy(ann, econ)

    notes_card([
        "Cases and deaths are monthly totals of reported daily figures (WHO via Our World "
        "in Data). Reported cases depend on testing, and reported deaths on registration "
        "rules; very low values (for example China's) do not prove a milder epidemic.",
        "The stringency index (Oxford COVID-19 Government Response Tracker, 0–100) "
        "describes containment rules, not compliance or effectiveness.",
        "Correlations use 21 country-years at most; observations from the same country are "
        "not independent and several tests are run at once.",
        "Annual totals for cases, deaths and stringency use the full 2020–2022 years, "
        "whatever the year filter.",
    ])


def show_policy_response():
    data = load_data_or_stop()
    countries, years = sidebar_filters(data["countries"])
    require_countries(countries)
    render_policy_response(data, countries, years)
