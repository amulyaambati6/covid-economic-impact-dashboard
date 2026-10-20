"""Shared page layout: navigation registry, headers, filters, and cards.

Every research page uses these helpers, so titles, filters, insight boxes
and limitation notes look and behave the same everywhere.
"""

import html

import streamlit as st

from src.visualizations.charts import COUNTRY_COLORS

ECONOMIC_YEAR_RANGE = (2018, 2024)

# Simple line icons (24 x 24, drawn with the current text colour).
ICONS = {
    "growth": '<path d="M4 20v-6M9 20v-9M14 20v-7M19 20V8"/><path d="M4 10l5-4 4 3 7-5"/><path d="M16.5 4H20v3.5"/>',
    "labour": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.4"/><path d="M3.5 20c0-3.2 2.5-5.6 5.5-5.6s5.5 2.4 5.5 5.6"/><path d="M15.2 14.6c2.9.1 5.3 2.2 5.3 5.4"/>',
    "inflation": '<ellipse cx="12" cy="5.5" rx="7" ry="2.5"/><path d="M5 5.5v4c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-4"/><path d="M5 9.5v4c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-4"/><path d="M5 13.5v4c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-4"/>',
    "policy": '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><path d="M10 11.5h5M10 14.5h5M10 17.5h3"/>',
    "comparison": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.4 2.6 3.7 5.6 3.7 9s-1.3 6.4-3.7 9c-2.4-2.6-3.7-5.6-3.7-9S9.6 5.6 12 3z"/>',
    "findings": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.6 10.8c.7.5 1.1 1.3 1.1 2.1v.1h5v-.1c0-.8.4-1.6 1.1-2.1A6 6 0 0 0 12 3z"/>',
    "home": '<path d="M4 11l8-7 8 7"/><path d="M6 9.5V20h12V9.5"/><path d="M10 20v-5h4v5"/>',
    "report": '<path d="M5 4h14v16H5z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "about": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.5v.5"/>',
}


def icon(name, size=24, css_class="icon"):
    """Inline SVG icon markup."""
    return (
        f'<svg class="{css_class}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
    )


# One registry for the six research pages. app.py builds the sidebar
# navigation from it and the homepage builds its cards from it, so a card
# always links to the page it names.
RESEARCH_PAGES = [
    {
        "key": "growth",
        "url_path": "economic-growth",
        "title": "Economic Growth",
        "question": "How did GDP growth change during and after the pandemic?",
        "card_question": "How did GDP change across countries?",
        "icon": "growth",
    },
    {
        "key": "labour",
        "url_path": "labour-market",
        "title": "Labour Market",
        "question": "How did unemployment change during and after the pandemic?",
        "card_question": "How was employment affected?",
        "icon": "labour",
    },
    {
        "key": "inflation",
        "url_path": "inflation",
        "title": "Inflation",
        "question": "How did consumer price inflation evolve during and after the pandemic?",
        "card_question": "How did prices change across countries?",
        "icon": "inflation",
    },
    {
        "key": "policy",
        "url_path": "pandemic-policy",
        "title": "Pandemic & Policy Response",
        "question": "How severe was the reported pandemic, how strict were governments, and did either track the economy?",
        "card_question": "How did governments respond?",
        "icon": "policy",
    },
    {
        "key": "comparison",
        "url_path": "country-comparisons",
        "title": "Country Comparisons",
        "question": "How did the seven countries compare on each indicator?",
        "card_question": "Compare key indicators across seven countries",
        "icon": "comparison",
    },
    {
        "key": "findings",
        "url_path": "key-findings",
        "title": "Key Findings",
        "question": "What do the data show, and what can they not show?",
        "card_question": "Main takeaways from our analysis",
        "icon": "findings",
    },
]

PAGE_BY_KEY = {page["key"]: page for page in RESEARCH_PAGES}


def apply_styles(css_text):
    """Inject the project stylesheet into the current page."""
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)


def html_block(markup):
    """Render trusted HTML. Blank lines and indentation are removed so that
    Markdown never turns indented HTML into a code block."""
    lines = [line.strip() for line in markup.splitlines()]
    st.markdown("\n".join(line for line in lines if line), unsafe_allow_html=True)


def page_header(page_key, description, number=None):
    """Title, one-sentence research question, and what the page examines."""
    page = PAGE_BY_KEY[page_key]
    position = RESEARCH_PAGES.index(page) + 1 if number is None else number
    html_block(f"""
    <header class="page-head">
    <div class="page-head__text">
    <p class="eyebrow">Research page {position} of {len(RESEARCH_PAGES)}</p>
    <h1 class="page-head__title">{html.escape(page['title'])}</h1>
    <p class="page-head__question">{html.escape(page['question'])}</p>
    <p class="page-head__lede">{description}</p>
    </div>
    <div class="page-head__icon">{icon(page['icon'], size=44)}</div>
    </header>
    """)


def section_title(text, subtitle=None):
    """A small serif section heading inside a page."""
    sub = f'<p class="section-sub">{subtitle}</p>' if subtitle else ""
    html_block(f'<div class="section-title"><h3>{text}</h3>{sub}</div>')


def insight_card(title, items):
    """Boxed list of short, data-based insights (items may contain <b>)."""
    if not items:
        return
    bullets = "".join(f"<li>{item}</li>" for item in items)
    html_block(
        f'<div class="insight-card"><h4>{icon("findings", 18)} {title}</h4>'
        f"<ul>{bullets}</ul></div>"
    )


def notes_card(items, title="Interpretation notes and limitations"):
    """Visible box with data limitations for the page."""
    bullets = "".join(f"<li>{item}</li>" for item in items)
    html_block(
        f'<div class="notes-card"><h4>{icon("about", 18)} {title}</h4>'
        f"<ul>{bullets}</ul></div>"
    )


def country_chip(country):
    """Country name with its fixed chart colour as a small dot."""
    color = COUNTRY_COLORS.get(country, "#6B7280")
    return (
        f'<span class="chip"><span class="chip__dot" style="background:{color}"></span>'
        f"{html.escape(country)}</span>"
    )


# ---------------------------------------------------------------------------
# Sidebar filters shared by every page
# ---------------------------------------------------------------------------
# A widget's value is normally forgotten when the user moves to a page that
# does not show it. Copying the value into a plain session-state key (and
# back before the widget is drawn) keeps the selection when switching pages.

def _remember(widget_key, store_key):
    st.session_state[store_key] = st.session_state[widget_key]


def _reset_filters(countries):
    st.session_state["filter_countries"] = list(countries)
    st.session_state["filter_years"] = ECONOMIC_YEAR_RANGE


def sidebar_filters(countries, show_years=True, year_help=None):
    """Draw the country (and optionally year-range) filters in the sidebar.

    Returns (selected_countries in fixed order, (start_year, end_year)).
    """
    st.session_state.setdefault("filter_countries", list(countries))
    st.session_state.setdefault("filter_years", ECONOMIC_YEAR_RANGE)

    st.sidebar.markdown("#### Filters")

    st.session_state["_countries_widget"] = [
        c for c in st.session_state["filter_countries"] if c in countries
    ]
    st.sidebar.multiselect(
        "Countries",
        options=countries,
        key="_countries_widget",
        on_change=_remember,
        args=("_countries_widget", "filter_countries"),
        help="Applies to every chart and summary on the research pages.",
    )

    years = st.session_state["filter_years"]
    if show_years:
        st.session_state["_years_widget"] = tuple(years)
        st.sidebar.slider(
            "Years shown",
            min_value=ECONOMIC_YEAR_RANGE[0],
            max_value=ECONOMIC_YEAR_RANGE[1],
            key="_years_widget",
            on_change=_remember,
            args=("_years_widget", "filter_years"),
            help=year_help or "Changes the years drawn in the time-series "
            "charts. Headline figures use fixed reference years.",
        )

    st.sidebar.button(
        "Reset filters",
        on_click=_reset_filters,
        args=(countries,),
        width="stretch",
    )
    st.sidebar.caption(
        "Each country keeps the same colour and marker on every chart."
    )

    selected = [c for c in countries if c in st.session_state["filter_countries"]]
    return selected, tuple(years)


def require_countries(selected):
    """Stop the page with a clear message if no country is selected."""
    if not selected:
        st.warning("Select at least one country in the sidebar to view this page.")
        st.stop()


def count_text(n, word="country", plural="countries"):
    """'1 country' / '3 countries'."""
    return f"{n} {word if n == 1 else plural}"


def load_data_or_stop():
    """Load the shared datasets, or show a clear error and stop the page."""
    from src.data.prepare import load_dashboard_data

    try:
        return load_dashboard_data()
    except Exception as exc:  # show any loading problem to the user
        st.error(f"Could not load the project datasets: {exc}")
        st.info("Check the processed CSV files in data/processed/ and src/data/loader.py.")
        st.stop()


def fmt(value, pattern="{:.1f}", missing="N/A"):
    """Format a number, or return 'N/A' for a missing value."""
    try:
        if value is None or value != value:  # NaN check
            return missing
    except TypeError:
        return missing
    return pattern.format(value)
