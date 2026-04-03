# -*- coding: utf-8 -*-
"""
Macro signal generation from news articles + market data.
Produces directional signals per currency pair.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Dict

log = logging.getLogger("terminal.signals")

HAWKISH_KEYWORDS = [
    "rate hike", "tightening", "inflation", "hawkish", "higher rates",
    "restrictive", "overheating", "wage growth", "price pressure",
]
DOVISH_KEYWORDS = [
    "rate cut", "easing", "dovish", "slowdown", "recession",
    "disinflation", "unemployment", "weaker", "accommodative",
]
RISK_ON_KEYWORDS = ["rally", "optimism", "growth", "recovery", "risk appetite"]
RISK_OFF_KEYWORDS = ["sell-off", "crisis", "fear", "volatility", "safe haven", "tariff", "trade war"]

FX_PAIRS = [
    ("EUR/USD", "EUR", "USD"), ("GBP/USD", "GBP", "USD"),
    ("USD/JPY", "USD", "JPY"), ("USD/CHF", "USD", "CHF"),
    ("AUD/USD", "AUD", "USD"), ("NZD/USD", "NZD", "USD"),
    ("USD/CAD", "USD", "CAD"),
]


def _score_text(text: str, keywords: list) -> float:
    text_lower = text.lower()
    count = 0
    for kw in keywords:
        count += len(re.findall(re.escape(kw), text_lower))
    return count


def _ccy_sentiment(articles: list) -> Dict[str, float]:
    """Score each currency with multi-day weighting (medium-term bias)."""
    scores = {}
    now = datetime.now(timezone.utc)
    for ccy in ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "NZD", "CHF"]:
        total = 0.0
        wsum = 0.0
        for art in articles:
            text = (art.get("title", "") + " " + art.get("summary", "")).upper()
            if ccy not in text:
                continue
            full = art.get("title", "") + " " + art.get("summary", "")
            hawk = _score_text(full, HAWKISH_KEYWORDS)
            dove = _score_text(full, DOVISH_KEYWORDS)
            # Medium-term decay: ~1.0 today, ~0.55 at 3d, ~0.3 around a week.
            w = 0.4
            pub = art.get("published_utc")
            if isinstance(pub, str) and pub:
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
                    w = 1.0 / (1.0 + 0.28 * age_days)
                except Exception:
                    pass
            total += (hawk - dove) * w
            wsum += w
        scores[ccy] = total / max(wsum, 1e-9)
    return scores


def generate_signals(articles: list, market_data: dict = None) -> List[dict]:
    """Generate medium-term (multi-day) macro FX signals from articles."""
    if not articles:
        return []

    ccy_scores = _ccy_sentiment(articles)
    signals = []

    for pair_name, base, quote in FX_PAIRS:
        base_score = ccy_scores.get(base, 0)
        quote_score = ccy_scores.get(quote, 0)
        diff = base_score - quote_score

        if abs(diff) < 0.1:
            continue

        direction = "LONG" if diff > 0 else "SHORT"
        conviction = min(abs(diff) / 3.0, 1.0)

        driver = []
        if abs(base_score) > abs(quote_score):
            driver.append(base + (" hawkish" if base_score > 0 else " dovish"))
        else:
            driver.append(quote + (" dovish" if quote_score > 0 else " hawkish"))

        dir_expl = (
            f"LONG {pair_name}: net news flow favors {base} over {quote} "
            f"(lexicon score {base_score:+.2f} vs {quote_score:+.2f})."
            if direction == "LONG"
            else f"SHORT {pair_name}: net news flow favors {quote} over {base} "
            f"(lexicon score {quote_score:+.2f} vs {base_score:+.2f})."
        )
        conv_expl = (
            f"Conviction {conviction:.0%} scales with |{base_score:.2f}-{quote_score:.2f}| "
            f"on hawk/dove keyword hits in titles mentioning both currencies; "
            f"capped at 100%."
        )
        signals.append({
            "pair": pair_name,
            "direction": direction,
            "conviction": round(conviction, 3),
            "driver": ", ".join(driver),
            "base_score": round(base_score, 2),
            "quote_score": round(quote_score, 2),
            "priced_in": None,
            "direction_explanation": dir_expl,
            "conviction_explanation": conv_expl,
            "horizon": "multi-day (3-10d)",
        })

    signals.sort(key=lambda s: s["conviction"], reverse=True)
    return signals
