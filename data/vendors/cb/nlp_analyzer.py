"""Fallback lexical analyzer for central bank tone."""

from __future__ import annotations

import re

_HAWK = re.compile(r"\b(hike|tighten|inflation risk|higher for longer)\b", re.I)
_DOVE = re.compile(r"\b(cut|easing|disinflation|support growth)\b", re.I)


def analyze_tone(text: str) -> dict:
    text = text or ""
    h = len(_HAWK.findall(text))
    d = len(_DOVE.findall(text))
    score = h - d
    if score > 1:
        tone = "hawkish"
    elif score < -1:
        tone = "dovish"
    else:
        tone = "neutral"
    return {"score": score, "tone": tone, "keywords": []}

