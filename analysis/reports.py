# -*- coding: utf-8 -*-
"""
AI intelligence report generation: morning brief + regional digests.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List

log = logging.getLogger("terminal.intel")

# Keywords / patterns to route articles into regional briefs (case-insensitive)
_US_PAT = re.compile(
    r"\b(fed|fomc|treasury|white house|cpi|nfp|jobs report|dollar index|"
    r"nasdaq|s&p|wall street|u\.s\.|united states|america|sec |cftc)\b",
    re.I,
)
_EU_PAT = re.compile(
    r"\b(ecb|eurozone|european central|lagarde|bundesbank|boe |bank of england|"
    r"euro\b|sterling|ftse|eu |\beur\b|brexit|ecb )\b",
    re.I,
)
_ASIA_PAT = re.compile(
    r"\b(boj|bank of japan|pboc|china |rba |rbnz|hong kong|singapore|"
    r"nikkei|shanghai|yen|yuan|aud|nzd|jpy|asia pacific)\b",
    re.I,
)


def _text(art: dict) -> str:
    return f"{art.get('title', '')} {art.get('summary', '')}"


def _score_region(art: dict, pattern: re.Pattern) -> int:
    return len(pattern.findall(_text(art)))


def _pick_articles(articles: list, region: str, limit: int = 14) -> List[dict]:
    """Pick best-matching articles for a region by keyword scoring."""
    if not articles:
        return []
    scored = []
    for a in articles:
        t = _text(a)
        s = 0
        if region == "us":
            s = _score_region(a, _US_PAT) * 2 + (1 if "USD" in t.upper() else 0)
        elif region == "europe":
            s = _score_region(a, _EU_PAT) * 2
            for w in ("EUR", "GBP", "CHF"):
                if w in t.upper():
                    s += 1
        elif region == "asia":
            s = _score_region(a, _ASIA_PAT) * 2
            for w in ("JPY", "CNY", "AUD", "NZD"):
                if w in t.upper():
                    s += 1
        else:  # global — wide lens: keyword-light articles still rank by general macro words
            s = _score_region(a, _US_PAT) + _score_region(a, _EU_PAT) + _score_region(a, _ASIA_PAT)
            s += min(len(t) // 400, 3)
        scored.append((s, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    seen = set()
    for _, a in scored:
        u = a.get("url") or a.get("title")
        if u in seen:
            continue
        seen.add(u)
        out.append(a)
        if len(out) >= limit:
            break
    return out


def _section_markdown(title: str, arts: List[dict], intro: str) -> str:
    lines = [f"## {title}", "", intro, ""]
    for art in arts:
        src = art.get("source", "News")[:40]
        lines.append(f"- **{src}**: {art.get('title', '')}")
    return "\n".join(lines)


def generate_brief(articles: list, cb_states: dict, calendar: list) -> Dict[str, Any]:
    """Full intel package: morning brief + US / Europe / Asia / Global digests."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # ── Morning brief (all hands)
    brief_lines = [f"## KMCO Morning Brief — {now.strftime('%A %d %B %Y')} UTC", ""]
    brief_lines.append("### Central bank wires")
    for bid, st in sorted(cb_states.items(), key=lambda x: x[0]):
        if st.get("last_title"):
            brief_lines.append(
                f"- **{st.get('bank_name', bid.upper())}**: {st['last_title']}"
            )

    brief_lines.extend(["", "### Headlines (cross-market)", ""])
    for art in articles[:18]:
        src = (art.get("source") or "")[:36]
        brief_lines.append(f"- **{src}**: {art.get('title', '')}")

    upcoming = [
        e for e in calendar
        if (e.get("date", "") > now_iso and e.get("impact") == "High")
    ]
    upcoming.sort(key=lambda e: e.get("date", ""))
    if upcoming:
        brief_lines.extend(["", "### High-impact calendar (next)", ""])
        for ev in upcoming[:10]:
            brief_lines.append(
                f"- {ev.get('country', '')} **{ev.get('title', '')}** — "
                f"{ev.get('date', '')[:16]}"
            )

    morning = "\n".join(brief_lines)

    arts_us = _pick_articles(articles, "us", 14)
    arts_eu = _pick_articles(articles, "europe", 14)
    arts_as = _pick_articles(articles, "asia", 14)
    arts_gl = _pick_articles(articles, "global", 16)

    us_txt = _section_markdown(
        "US — Rates, USD & data",
        arts_us,
        "Articles weighted toward Fed, US data, USD assets, and Washington policy.",
    )
    eu_txt = _section_markdown(
        "Europe — ECB, BoE & euro area",
        arts_eu,
        "Weighted toward ECB/BoE, EUR/GBP/CHF macro and EU politics.",
    )
    asia_txt = _section_markdown(
        "Asia-Pacific — BoJ, China, commodities",
        arts_as,
        "Weighted toward Japan, China, Australia/NZ and regional FX.",
    )
    global_txt = _section_markdown(
        "Global — Cross-asset & macro",
        arts_gl,
        "Broad macro and cross-market stories (filtered from the full wire).",
    )

    return {
        "brief": morning,
        "us": us_txt,
        "europe": eu_txt,
        "asia": asia_txt,
        "global": global_txt,
        "generated_at": now_iso,
    }


REPORT_SCHEMA_VERSION = 2


def generate_session_report(
    articles: list,
    cb_states: dict,
    calendar: list,
    market: Dict[str, Any],
) -> Dict[str, Any]:
    """Rapport de session structuré : blocs reproductibles + JSON canonique + bundle markdown."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    base = generate_brief(articles, cb_states, calendar)
    overnight_md = base["brief"]
    europe_md = base["europe"]
    us_md = base["us"]
    asia_md = base["asia"]
    global_md = base["global"]
    eod_md = (
        "### EOD wrap\n\nSynthèse fin de séance : croiser actuals calendrier vs fil live.\n\n"
        + asia_md
        + "\n\n"
        + global_md
    )
    sourcing = {
        "wire_article_count": len(articles or []),
        "cb_banks_with_title": len([1 for s in (cb_states or {}).values() if s.get("last_title")]),
        "calendar_row_count": len(calendar or []),
        "market_instrument_count": len((market or {}).get("instruments") or []),
    }
    bundle = "\n\n---\n\n".join([overnight_md, europe_md, us_md, asia_md, global_md])
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generator": "terminal.analysis.reports.generate_session_report",
        "generated_at_utc": now_iso,
        "sections": {
            "overnight": {"title": "Overnight / handoff", "markdown": overnight_md},
            "europe": {"title": "Europe", "markdown": europe_md},
            "us": {"title": "US", "markdown": us_md},
            "eod": {"title": "Asia / Global / EOD", "markdown": eod_md},
        },
        "markdown_bundle": bundle,
        "sourcing": sourcing,
        "legacy_brief": base,
    }
