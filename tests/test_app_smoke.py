"""Smoke tests: the Streamlit app and every page render without errors.

Uses Streamlit's built-in testing tool (no browser needed). Run from the
project root with:  python -m unittest discover -s tests
"""
import ast
import json
import re
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.visualizations.charts import COUNTRY_COLORS, COUNTRY_ORDER
from src.visualizations.layout import RESEARCH_PAGES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 120

PAGES = {
    "landing": "show_landing",
    "economic_growth": "show_economic_growth",
    "labour_market": "show_labour_market",
    "inflation": "show_inflation",
    "policy_response": "show_policy_response",
    "country_comparison": "show_country_comparison",
    "key_findings": "show_key_findings",
    "home": "show_home",
    "overview": "show_overview",
}

# A tiny script that runs one page function with the project on the path.
PAGE_SCRIPT = """
import sys
sys.path.insert(0, {root!r})
from pages.{module} import {function}
{function}()
"""


def run_page(module):
    script = PAGE_SCRIPT.format(
        root=str(PROJECT_ROOT), module=module, function=PAGES[module]
    )
    return AppTest.from_string(script, default_timeout=TIMEOUT).run()


def chart_trace_colors(app):
    """Return {chart title: {trace name: colour}} for every Plotly chart."""
    charts = {}
    for element in app.get("plotly_chart"):
        spec = json.loads(element.proto.spec)
        title = spec["layout"].get("title", {}).get("text", "")
        colors = {}
        for trace in spec["data"]:
            color = (trace.get("line") or {}).get("color") or (
                trace.get("marker") or {}
            ).get("color")
            if isinstance(color, str) and trace.get("name"):
                colors[trace["name"]] = color
        charts[title] = colors
    return charts


def all_text(app):
    return " ".join(m.value for m in app.markdown) + " ".join(
        i.value for i in app.info
    )


class AppStartupTests(unittest.TestCase):
    def test_entry_point_runs(self):
        app = AppTest.from_file(
            str(PROJECT_ROOT / "app.py"), default_timeout=TIMEOUT
        ).run()
        self.assertEqual(len(app.exception), 0, app.exception)
        self.assertIn("How did the COVID-19 pandemic impact", all_text(app))

    def test_every_page_renders(self):
        for module in PAGES:
            with self.subTest(page=module):
                app = run_page(module)
                self.assertEqual(
                    len(app.exception), 0, [e.message for e in app.exception]
                )
                self.assertEqual(len(app.error), 0, [e.value for e in app.error])


class NavigationTests(unittest.TestCase):
    def test_homepage_cards_link_to_registered_pages(self):
        text = all_text(run_page("landing"))
        links = set(re.findall(r'class="orbit-card[^"]*" href="([^"]+)"', text))
        self.assertEqual(links, {p["url_path"] for p in RESEARCH_PAGES})
        self.assertIn('class="btn-primary" href="economic-growth"', text)

    def test_app_registers_every_url_path(self):
        source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        # The research pages take their url_path from RESEARCH_PAGES, and the
        # app maps every registry key to a page function.
        self.assertIn('url_path=page["url_path"]', source)
        mapping = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and getattr(node.targets[0], "id", "") == "RESEARCH_FUNCTIONS"
        )
        keys = {k.value for k in mapping.value.keys}
        self.assertEqual(keys, {p["key"] for p in RESEARCH_PAGES})


class ResearchPageTests(unittest.TestCase):
    def assert_clean(self, app):
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
        self.assertEqual(len(app.error), 0, [e.value for e in app.error])

    def test_headline_kpis_match_processed_data(self):
        expected = {
            "economic_growth": {
                "Median GDP growth, 2019": "2.6%",
                "Median GDP growth, 2020": "-3.3%",
                "Median GDP growth, 2021": "6.9%",
                "Contracted in 2020": "6 of 7",
            },
            "labour_market": {
                "Median unemployment, 2019": "6.5%",
                "Median unemployment, 2020": "8.0%",
                "Biggest rise, 2019 to 2020": "+4.4 pp",
            },
            "inflation": {
                "Median inflation, 2020": "2.4%",
                "Median inflation, 2022": "6.9%",
                "Highest annual rate, 2018–24": "19.8%",
            },
            "policy_response": {
                "Highest reported deaths per million, 2020–22": "3,296",
                "Strictest month (stringency 0–100)": "98.6",
            },
        }
        for module, kpis in expected.items():
            with self.subTest(page=module):
                metrics = {m.label: m.value for m in run_page(module).metric}
                for label, value in kpis.items():
                    self.assertEqual(metrics[label], value)

    def test_no_strongest_correlation_headline(self):
        app = run_page("policy_response")
        text = all_text(app)
        self.assertNotIn("Strongest observed", text)
        self.assertIn("Bonferroni", text)
        self.assertIn("not consistent within years", text)

    def test_country_colours_are_fixed_on_every_chart(self):
        for module in ["economic_growth", "labour_market", "inflation",
                       "policy_response", "country_comparison"]:
            for title, colors in chart_trace_colors(run_page(module)).items():
                for name, color in colors.items():
                    country = name.split(",")[0]
                    if country in COUNTRY_COLORS:
                        self.assertEqual(
                            color, COUNTRY_COLORS[country], f"{country}: {title}"
                        )

    def test_filters_and_colours_after_selection_change(self):
        app = run_page("economic_growth")
        app.multiselect[0].set_value(["Rwanda", "Germany"]).run()
        self.assert_clean(app)
        seen = set()
        for colors in chart_trace_colors(app).values():
            for name, color in colors.items():
                country = name.split(",")[0]
                if country in COUNTRY_COLORS:
                    seen.add(country)
                    self.assertEqual(color, COUNTRY_COLORS[country])
        self.assertEqual(seen, {"Rwanda", "Germany"})

    def test_representative_filter_combinations(self):
        for module in ["economic_growth", "labour_market", "inflation",
                       "policy_response", "country_comparison"]:
            app = run_page(module)
            for selection in [[], ["China"], ["India", "Brazil"], COUNTRY_ORDER[::-1]]:
                with self.subTest(page=module, selection=selection):
                    app.multiselect[0].set_value(selection).run()
                    self.assert_clean(app)
                    if not selection:
                        self.assertTrue(any(
                            "Select at least one country" in w.value
                            for w in app.warning
                        ))

    def test_year_range_filter(self):
        app = run_page("economic_growth")
        for years in [(2018, 2024), (2020, 2022), (2023, 2024)]:
            app.slider[0].set_value(years).run()
            self.assert_clean(app)
        app = run_page("policy_response")
        app.slider[0].set_value((2023, 2024)).run()
        self.assert_clean(app)
        self.assertTrue(any("2020–2022 only" in i.value for i in app.info))

    def test_policy_page_options(self):
        app = run_page("policy_response")
        for indicator in app.radio(key="policy_health_indicator").options:
            app.radio(key="policy_health_indicator").set_value(indicator).run()
            for scale in app.radio(key="health_scale").options:
                app.radio(key="health_scale").set_value(scale).run()
                self.assert_clean(app)
        for view in app.radio(key="policy_stringency_view").options:
            app.radio(key="policy_stringency_view").set_value(view).run()
            self.assert_clean(app)

    def test_comparison_page_every_indicator_and_year(self):
        app = run_page("country_comparison")
        for indicator in app.selectbox(key="compare_indicator").options:
            app.selectbox(key="compare_indicator").set_value(indicator).run()
            self.assert_clean(app)
            year_box = [s for s in app.selectbox if s.key.startswith("compare_year")][0]
            for year in year_box.options:
                year_box.set_value(year).run()
                self.assert_clean(app)
                year_box = [s for s in app.selectbox
                            if s.key.startswith("compare_year")][0]


if __name__ == "__main__":
    unittest.main()
