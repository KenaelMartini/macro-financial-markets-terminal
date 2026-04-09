# -*- coding: utf-8 -*-
"""
Tonalité affichée côté terminal : lexique sur le **dernier titre du poll RSS/HTML** (fil live).
Ce n’est **pas** une lecture du marché (pas d’OIS, pas de pricing implicite).

Les anciens events.jsonl peuvent contenir des entrées de démo — on les filtre à l’import.
"""

from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import CB_DIR

# ── Charger nlp_analyzer du repo Central Bank Monitoring (sans dépendre du package) ──


def _analyze_tone(text: str) -> Dict[str, Any]:
    path = CB_DIR / "nlp_analyzer.py"
    if not path.exists():
        return {"score": 0, "tone": "neutral", "keywords": []}
    spec = importlib.util.spec_from_file_location("cb_nlp_lexicon", path)
    if spec is None or spec.loader is None:
        return {"score": 0, "tone": "neutral", "keywords": []}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.analyze_tone(text or "")


_DEMO_MARKERS = (
    "pour tester",
    "orientation hawkish",
    "orientation dovish",
    "non précisé (démo)",
    "non precise (demo)",
    "synthèse démo",
    "synthese demo",
)

_GARBAGE_RE = re.compile(
    r'^[\s"\'zr.]{0,20}$|(.)\1{5,}|["\'][a-z]{0,2}["\']',
    re.I,
)

# Titres de test / démo dans les JSONL (ex. "… (DEMO)")
_DEMO_TITLE_RE = re.compile(
    r"\(demo\)|\(démo\)|\bdemo\s*\)|\s\(demo\)\s*$|\[demo\]|\btest\s+ui\b",
    re.I,
)


def trustworthy_title(title: str) -> bool:
    t = (title or "").strip()
    if len(t) < 8:
        return False
    low = t.lower()
    if any(m in low for m in _DEMO_MARKERS):
        return False
    if _DEMO_TITLE_RE.search(t):
        return False
    if _GARBAGE_RE.search(t):
        return False
    return True


def filter_stored_cb_event(ev: Dict[str, Any]) -> bool:
    """Exclut démo / titres pourris des JSONL."""
    if not isinstance(ev, dict):
        return False
    t = (ev.get("title") or "").strip()
    if _DEMO_TITLE_RE.search(t):
        return False
    if not trustworthy_title(t):
        return False
    blob = json.dumps(ev.get("analysis") or {}, ensure_ascii=False).lower()
    low = t.lower() + " " + blob
    if any(m in low for m in _DEMO_MARKERS):
        return False
    if _DEMO_TITLE_RE.search(blob):
        return False
    return True


def _triplet_from_score(score: int) -> Tuple[int, int, int]:
    """Approximation Dov / Neu / Haw en % pour l’UI (somme ≈ 100)."""
    s = max(-12, min(12, int(score)))
    d_mass = float(max(0, -s))
    h_mass = float(max(0, s))
    n_mass = 4.0
    tot = d_mass + n_mass + h_mass
    if tot <= 0:
        return 33, 34, 33
    d = int(round(100 * d_mass / tot))
    h = int(round(100 * h_mass / tot))
    n = 100 - d - h
    return d, max(0, n), h


def net_hawk_from_triplet(d: int, n: int, h: int) -> Optional[float]:
    t = d + n + h
    if t <= 0:
        return None
    return (h - d) / t


def wire_lexicon_block(title: Optional[str], extended_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Analyse lexicale sur le titre du dernier poll ; si extended_text (corps HTML nettoyé),
    le lexique s’applique au bloc titre + corps (tronqué).
    """
    if not title or not trustworthy_title(title):
        return None
    blob = title
    if extended_text and extended_text.strip():
        blob = f"{title}\n{extended_text.strip()}"[:20000]
    an = _analyze_tone(blob)
    score = int(an.get("score") or 0)
    d, n, h = _triplet_from_score(score)
    nh = net_hawk_from_triplet(d, n, h)
    return {
        "mode": "lexicon_on_latest_poll_title_plus_body" if extended_text else "lexicon_on_latest_poll_title",
        "disclaimer": (
            "Analyse par mots-clés sur le dernier titre"
            + (" et un extrait de la page" if extended_text else "")
            + " récupéré du site/RSS de la banque. Ce n’est pas le ton ‘implicite’ du marché (swaps, OIS, FX)."
        ),
        "score": score,
        "tone": an.get("tone") or "neutral",
        "keywords": (an.get("keywords") or [])[:12],
        "triplet_dnh": [d, n, h],
        "net_hawk": round(nh, 4) if nh is not None else None,
    }


def enrich_cb_state(bank_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Copie l’état banque + ajoute wire_lexicon + snapshots daily (AM/PM)."""
    out = dict(state)
    title = out.get("last_title") or ""
    excerpt = (out.get("communication_excerpt") or "").strip()
    current = wire_lexicon_block(title, extended_text=excerpt or None)
    out["wire_lexicon"] = current
    out["wire_lexicon_title_used"] = title if out["wire_lexicon"] else None
    # Daily cadence snapshot: morning / evening (UTC), keep unchanged if no new signal.
    now = datetime.now(timezone.utc)
    slot = "morning" if 4 <= now.hour < 16 else "evening"
    fp = (title or "").strip().lower()
    prev_fp = str(out.get(f"daily_{slot}_title_fp") or "")
    prev_block = out.get(f"last_{slot}_analysis")
    unchanged = bool(fp and prev_fp and fp == prev_fp)
    if unchanged and prev_block:
        out["wire_lexicon"] = prev_block
        out["tone_unchanged"] = True
    else:
        out[f"last_{slot}_analysis"] = out["wire_lexicon"]
        out[f"last_{slot}_analysis_ts"] = now.isoformat()
        out[f"daily_{slot}_title_fp"] = fp
        out["tone_unchanged"] = False
    wl = out.get("wire_lexicon") or {}
    nh = wl.get("net_hawk")
    try:
        from analysis.nlp_cb_desk import build_desk_scores, tone_shift_vs_history

        out["tone_shift"] = tone_shift_vs_history(bank_id, nh)
        blob = f"{title}\n{excerpt}".strip() if excerpt else title
        if len(blob) >= 12:
            dk = build_desk_scores(blob, title=title)
            out["desk_preview"] = {
                "forward_guidance": dk.get("forward_guidance"),
                "surprise_proxy": dk.get("surprise_proxy"),
            }
    except Exception:
        out["tone_shift"] = {"interpretation": "unavailable"}
    return out
