# -*- coding: utf-8 -*-
"""
Scores NLP « desk » multi-dimensions (règles + lexique titre/corps) et tone shift vs fenêtre SQLite.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from analysis.cb_tone_live import _analyze_tone, net_hawk_from_triplet, _triplet_from_score

SCHEMA_VERSION = 1

_FG_HAWKISH = re.compile(
    r"\b(higher for longer|restrictive|tighten|tightening|hike|rate increase|"
    r"further tightening|no cuts|pause is not|inflation risks|upside risks)\b",
    re.I,
)
_FG_DOVISH = re.compile(
    r"\b(cut rates|rate cut|easing|accommodative|patient|data dependent|"
    r"downside risks|disinflation|soft landing)\b",
    re.I,
)
_SURPRISE = re.compile(
    r"\b(surprise|unexpected|sharply|unscheduled|emergency|"
    r"larger than expected|smaller than expected)\b",
    re.I,
)


def _fg_score(text: str) -> float:
    t = text or ""
    h = len(_FG_HAWKISH.findall(t))
    d = len(_FG_DOVISH.findall(t))
    if h == d == 0:
        return 0.0
    return max(-1.0, min(1.0, (h - d) / max(h + d, 1)))


def _surprise_proxy(text: str) -> float:
    t = text or ""
    return min(1.0, len(_SURPRISE.findall(t)) * 0.35)


def build_desk_scores(full_text: str, title: str = "") -> Dict[str, Any]:
    """Analyse sur texte concaténé (titre + corps page si dispo)."""
    blob = f"{title}\n\n{full_text}".strip()
    if len(blob) < 8:
        return {
            "schema_version": SCHEMA_VERSION,
            "tone": "neutral",
            "lexicon_score": 0,
            "forward_guidance": 0.0,
            "surprise_proxy": 0.0,
            "net_hawk": None,
            "triplet_dnh": [33, 34, 33],
        }
    an = _analyze_tone(blob)
    score = int(an.get("score") or 0)
    d, n, h = _triplet_from_score(score)
    nh = net_hawk_from_triplet(d, n, h)
    fg = _fg_score(blob)
    sp = _surprise_proxy(blob)
    tone = str(an.get("tone") or "neutral")
    return {
        "schema_version": SCHEMA_VERSION,
        "tone": tone,
        "lexicon_score": score,
        "forward_guidance": round(fg, 4),
        "surprise_proxy": round(sp, 4),
        "net_hawk": round(nh, 4) if nh is not None else None,
        "triplet_dnh": [d, n, h],
        "keywords": (an.get("keywords") or [])[:16],
        "text_chars_analyzed": len(blob),
    }


def tone_shift_vs_history(bank_id: str, current_net_hawk: Optional[float], window: int = 30) -> Dict[str, Any]:
    """Compare le net_hawk courant à la moyenne des derniers scores persistés."""
    out: Dict[str, Any] = {
        "window_rows": window,
        "baseline_net_hawk": None,
        "delta_net_hawk": None,
        "interpretation": "insufficient_history",
    }
    if current_net_hawk is None:
        out["interpretation"] = "no_current_score"
        return out
    try:
        from storage.sqlite_store import fetch_nlp_history
    except Exception:
        return out

    hist: List[dict] = fetch_nlp_history(bank_id, limit=window)
    nets: List[float] = []
    for row in hist:
        try:
            sj = row.get("scores") or {}
            v = sj.get("net_hawk")
            if v is not None:
                nets.append(float(v))
        except Exception:
            continue
    if len(nets) < 3:
        out["interpretation"] = "warming_up"
        return out
    avg = sum(nets) / len(nets)
    delta = current_net_hawk - avg
    out["baseline_net_hawk"] = round(avg, 4)
    out["delta_net_hawk"] = round(delta, 4)
    if delta > 0.08:
        out["interpretation"] = "hawkish_vs_window"
    elif delta < -0.08:
        out["interpretation"] = "dovish_vs_window"
    else:
        out["interpretation"] = "inline_with_window"
    return out


def desk_payload_for_bank(bank_id: str, enriched_state: Dict[str, Any]) -> Dict[str, Any]:
    title = (enriched_state.get("last_title") or "").strip()
    excerpt = (enriched_state.get("communication_excerpt") or "").strip()
    full = f"{title}\n{excerpt}".strip() if excerpt else title
    desk = build_desk_scores(full, title=title)
    desk["tone_shift"] = tone_shift_vs_history(bank_id, desk.get("net_hawk"))
    desk["wire_lexicon"] = enriched_state.get("wire_lexicon")
    return desk
