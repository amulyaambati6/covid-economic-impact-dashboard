"""Homepage: the research question, the virus-and-globe illustration, and
six navigation cards that link to the research pages.

The illustration is inline SVG drawn in code (no image files), so it loads
instantly and scales without blurring. The cards are ordinary links: they
are always visible and work with a mouse, a keyboard (Tab / Enter), and a
touchscreen. Hovering the virus only adds emphasis.
"""

import math

import streamlit as st

from src.data.prepare import load_dashboard_data
from src.visualizations.layout import (
    RESEARCH_PAGES,
    html_block,
    icon,
)

# Where each card sits around the illustration (percent of the orbit box)
# and the connector curve (in SVG units, viewBox 760 x 600) that joins it.
CARD_LAYOUT = {
    "growth": {"left": 5, "top": 1, "link": "M262 170 C232 140 200 120 170 104"},
    "labour": {"left": 66, "top": 3, "link": "M404 166 C440 132 478 112 520 100"},
    "inflation": {"left": 71, "top": 37, "link": "M512 300 C522 288 532 280 545 276"},
    "policy": {"left": 66, "top": 72, "link": "M474 410 C488 420 500 428 516 436"},
    "comparison": {"left": 0, "top": 55, "link": "M198 318 C188 326 176 334 160 340"},
    "findings": {"left": 27, "top": 83, "link": "M322 428 C318 452 314 474 312 496"},
}

GLOBE = (330, 280, 145)   # centre x, centre y, radius
VIRUS = (408, 338, 72)    # centre x, centre y, body radius


def _virus_spikes():
    """Spikes with knobbed tips, slightly irregular so they look hand-drawn."""
    cx, cy, r = VIRUS
    parts = []
    for i in range(18):
        angle = math.radians(i * 20 + (7 if i % 2 else 0))
        length = 30 + (i * 7) % 11          # 30-40 units, deterministic
        knob = 7.5 + (i * 5) % 3            # 7.5-9.5 units
        x1 = cx + (r - 4) * math.cos(angle)
        y1 = cy + (r - 4) * math.sin(angle)
        x2 = cx + (r + length) * math.cos(angle)
        y2 = cy + (r + length) * math.sin(angle)
        # slight bend in each stem
        bend = 4 if i % 3 else -4
        mx = (x1 + x2) / 2 - bend * math.sin(angle)
        my = (y1 + y2) / 2 + bend * math.cos(angle)
        parts.append(
            f'<path class="spike" d="M{x1:.1f} {y1:.1f} Q{mx:.1f} {my:.1f} {x2:.1f} {y2:.1f}"/>'
            f'<circle class="knob" cx="{x2:.1f}" cy="{y2:.1f}" r="{knob}"/>'
            f'<circle class="knob-hi" cx="{x2 - 2.5:.1f}" cy="{y2 - 2.5:.1f}" r="{knob / 3:.1f}"/>'
        )
    return "".join(parts)


def _virus_surface():
    """Pits and short strokes on the virus body."""
    cx, cy, _ = VIRUS
    pits = [(-30, -22, 6), (18, -34, 4.5), (34, 6, 5.5), (-8, 18, 7),
            (-38, 16, 4), (12, 40, 4.5), (40, -24, 3.5), (-16, -44, 3.5),
            (-44, -4, 3)]
    out = "".join(
        f'<circle class="pit" cx="{cx + dx}" cy="{cy + dy}" r="{pr}"/>'
        for dx, dy, pr in pits
    )
    strokes = [(-20, -5, 10, -12), (5, 22, 24, 16), (-28, 34, -12, 44),
               (22, -10, 36, -18)]
    out += "".join(
        f'<path class="texture" d="M{cx + a} {cy + b} Q{cx + (a + c) / 2} '
        f'{cy + (b + d) / 2 - 5} {cx + c} {cy + d}"/>'
        for a, b, c, d in strokes
    )
    return out


def _globe_lines():
    """Meridians and parallels in light strokes."""
    cx, cy, r = GLOBE
    lines = [f'<line class="grid-line" x1="{cx}" y1="{cy - r}" x2="{cx}" y2="{cy + r}"/>']
    for rx in (52, 100, 132):
        lines.append(
            f'<ellipse class="grid-line" cx="{cx}" cy="{cy}" rx="{rx}" ry="{r}"/>'
        )
    for dy, ry in ((-100, 7), (-55, 11), (0, 15), (55, 11), (100, 7)):
        rx = math.sqrt(r * r - dy * dy)
        lines.append(
            f'<ellipse class="grid-line" cx="{cx}" cy="{cy + dy}" rx="{rx:.1f}" ry="{ry}"/>'
        )
    return "".join(lines)


# Stylised continents (Americas, Europe, Africa) - illustrative, not a map.
CONTINENTS = [
    "M222 168 C240 150 275 146 300 152 C318 156 322 172 310 182 C298 190 300 205 "
    "286 214 C272 222 262 238 250 236 C236 234 232 220 222 214 C210 206 204 186 222 168 Z",
    "M262 246 C276 244 290 252 296 266 C306 286 300 312 292 332 C286 348 278 366 268 "
    "374 C262 360 262 340 256 322 C248 300 240 284 246 266 C250 256 254 248 262 246 Z",
    "M352 166 C366 158 386 160 398 168 C406 176 400 188 388 190 C376 192 366 196 356 "
    "192 C344 188 340 176 352 166 Z",
    "M360 206 C380 200 404 206 414 224 C424 242 420 264 408 282 C398 298 392 320 380 "
    "332 C372 320 370 302 362 288 C352 272 344 254 346 236 C348 222 350 210 360 206 Z",
    "M300 132 C312 126 328 128 332 138 C334 146 322 150 310 148 C300 146 294 138 300 132 Z",
]


def illustration_svg():
    """The full hand-drawn-style illustration with card connectors."""
    gx, gy, gr = GLOBE
    vx, vy, vr = VIRUS
    links = "".join(
        f'<path class="link link-{key}" d="{spec["link"]}"/>'
        for key, spec in CARD_LAYOUT.items()
    )
    continents = "".join(f'<path class="land" d="{d}"/>' for d in CONTINENTS)
    splashes = "".join(
        f'<circle class="splash" cx="{x}" cy="{y}" r="{r}"/>'
        for x, y, r in ((250, 210, 120), (470, 380, 110), (520, 190, 60))
    )
    dots = "".join(
        f'<circle class="speck" cx="{x}" cy="{y}" r="{r}"/>'
        for x, y, r in ((560, 150, 3), (588, 172, 2), (214, 452, 2.5),
                        (546, 470, 3.5), (170, 236, 2), (612, 330, 2.5),
                        (470, 120, 2), (250, 488, 3))
    )
    return f"""
    <svg class="orbit-art" viewBox="0 0 760 600" role="img"
    aria-label="Hand-drawn illustration of a coronavirus overlapping a globe">
    <defs>
    <filter id="pencil" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="4"/>
    <feDisplacementMap in="SourceGraphic" scale="2.6"/>
    </filter>
    <filter id="wash" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="26"/>
    </filter>
    <radialGradient id="ocean" cx="38%" cy="32%" r="75%">
    <stop offset="0%" stop-color="#EAF3F6"/>
    <stop offset="55%" stop-color="#BFD7E3"/>
    <stop offset="100%" stop-color="#8FB2C6"/>
    </radialGradient>
    <radialGradient id="body" cx="40%" cy="35%" r="70%">
    <stop offset="0%" stop-color="#F8CFD4"/>
    <stop offset="55%" stop-color="#E395A0"/>
    <stop offset="100%" stop-color="#C05E71"/>
    </radialGradient>
    <clipPath id="globe-clip"><circle cx="{gx}" cy="{gy}" r="{gr}"/></clipPath>
    </defs>
    <g class="washes" filter="url(#wash)">{splashes}</g>
    <g class="links">{links}</g>
    <g class="float">
    <g class="globe">
    <circle cx="{gx}" cy="{gy}" r="{gr}" fill="url(#ocean)"/>
    <g clip-path="url(#globe-clip)">
    {continents}
    {_globe_lines()}
    <circle cx="{gx + 60}" cy="{gy + 55}" r="{gr}" class="globe-shade"/>
    </g>
    <circle cx="{gx}" cy="{gy}" r="{gr}" class="globe-outline" filter="url(#pencil)"/>
    </g>
    <g class="virus">
    <g class="virus-spin">
    <g filter="url(#pencil)">{_virus_spikes()}</g>
    <circle cx="{vx}" cy="{vy}" r="{vr}" fill="url(#body)"/>
    <circle cx="{vx}" cy="{vy}" r="{vr}" class="virus-outline" filter="url(#pencil)"/>
    {_virus_surface()}
    </g>
    </g>
    </g>
    <g class="specks">{dots}</g>
    </svg>
    """


def orbit_cards():
    """The six navigation cards, positioned around the illustration."""
    cards = []
    for page in RESEARCH_PAGES:
        spec = CARD_LAYOUT[page["key"]]
        cards.append(f"""
        <a class="orbit-card orbit-card--{page['key']}" href="{page['url_path']}"
        target="_self" style="left:{spec['left']}%;top:{spec['top']}%">
        <span class="orbit-card__icon">{icon(page['icon'], 26)}</span>
        <span class="orbit-card__text">
        <span class="orbit-card__title">{page['title']}</span>
        <span class="orbit-card__q">{page['card_question']}</span>
        </span>
        </a>
        """)
    return "".join(cards)


def coverage_stats(data):
    """Facts for the stat strip, read from the data rather than typed in."""
    econ_years = data["economic"]["year"]
    pandemic_years = data["annual"]["year"]
    return {
        "countries": len(data["countries"]),
        "indicators": 6,  # 3 economic + cases, deaths, stringency
        "economy": f"{econ_years.min()}–{econ_years.max()}",
        "pandemic": f"{pandemic_years.min()}–{pandemic_years.max()}",
    }


def show_landing():
    try:
        data = load_dashboard_data()
        stats = coverage_stats(data)
    except Exception as exc:
        st.error(f"Could not load the project datasets: {exc}")
        return

    first_page = RESEARCH_PAGES[0]["url_path"]
    html_block(f"""
    <div class="hero-wrap">
    <section class="hero">
    <div class="hero__text">
    <p class="eyebrow">CentraleDigitalLab · Data Storytelling</p>
    <h1 class="hero__title">How did the COVID-19 pandemic impact the <em>global economy?</em></h1>
    <p class="hero__lede">Explore how the pandemic shaped economic growth, employment, prices,
    and policy responses across seven countries: the United States, India, France, China,
    Brazil, Germany, and Rwanda.</p>
    <a class="btn-primary" href="{first_page}" target="_self">Explore the data
    <span aria-hidden="true">→</span></a>
    <ul class="stat-strip">
    <li>{icon('comparison', 22)}<span><b>{stats['countries']}</b> countries</span></li>
    <li>{icon('growth', 22)}<span><b>{stats['indicators']}</b> indicators</span></li>
    <li>{icon('report', 22)}<span><b>{stats['economy']}</b> economy</span></li>
    <li>{icon('policy', 22)}<span><b>{stats['pandemic']}</b> pandemic</span></li>
    </ul>
    </div>
    <nav class="orbit" aria-label="Research pages">
    {illustration_svg()}
    {orbit_cards()}
    <p class="orbit-hint">Hover over the virus, or choose a topic</p>
    </nav>
    </section>
    </div>
    """)

    html_block(f"""
    <section class="explainer">
    <div class="explainer__item">
    <h4>{icon('comparison', 20)} Each country against its own normal</h4>
    <p>Most comparisons subtract a country's 2018–2019 average, so fast- and
    slow-growing economies can be compared fairly. Differences are in percentage points (pp).</p>
    </div>
    <div class="explainer__item">
    <h4>{icon('findings', 20)} Descriptive, not causal</h4>
    <p>The charts show when and how much indicators changed. Other shocks happened at the
    same time, so the data cannot isolate the effect of COVID-19 alone.</p>
    </div>
    <div class="explainer__item">
    <h4>{icon('report', 20)} Real, documented data</h4>
    <p>World Bank indicators, WHO cases and deaths, and the Oxford stringency index,
    cleaned with the scripts in this project. Sources and methods are on the
    <a href="about" target="_self">About &amp; methods</a> page.</p>
    </div>
    </section>
    """)
