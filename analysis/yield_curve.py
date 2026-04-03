# -*- coding: utf-8 -*-
"""
Courbes US Treasury via FRED (2Y/5Y/10Y/30Y) et spreads 2s10s, 5s30s.
Sans FRED_API_KEY, renvoie un squelette avec hint (pas de clé secrète embarquée).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from config import FRED_API_KEY

log = logging.getLogger("terminal.yields")

_FRED_OBS = "https://api.stlouisfed.org/fred/series/observations"

_SERIES = {
    "US2Y": "DGS2",
    "US5Y": "DGS5",
    "US10Y": "DGS10",
    "US30Y": "DGS30",
}


def _fred_latest(series_id: str) -> Optional[float]:
    if not FRED_API_KEY:
        return None
    try:
        r = requests.get(
            _FRED_OBS,
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,
            },
            timeout=12,
        )
        r.raise_for_status()
        obs = (r.json().get("observations") or [])
        if not obs:
            return None
        v = (obs[0].get("value") or "").strip()
        if v in (".", "", "nan"):
            return None
        return float(v)
    except Exception as e:
        log.debug("FRED %s: %s", series_id, e)
        return None


def build_yield_curve_payload() -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    pts: Dict[str, Optional[float]] = {}
    for label, sid in _SERIES.items():
        pts[label] = _fred_latest(sid)

    y2 = pts.get("US2Y")
    y5 = pts.get("US5Y")
    y10 = pts.get("US10Y")
    y30 = pts.get("US30Y")

    def spr(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return round(b - a, 4)

    out: Dict[str, Any] = {
        "schema_version": 1,
        "as_of_utc": now,
        "source": "fred" if FRED_API_KEY else "unconfigured",
        "currency": "USD",
        "instruments": [
            {"tenor": k, "fred_id": _SERIES[k], "yield_pct": v}
            for k, v in pts.items()
        ],
        "spreads": {
            "2s10s_bp": spr(y2, y10) * 100 if y2 is not None and y10 is not None else None,
            "5s30s_bp": spr(y5, y30) * 100 if y5 is not None and y30 is not None else None,
        },
    }
    if not FRED_API_KEY:
        out["error"] = "missing_fred_key"
        out["hint"] = "Définir FRED_API_KEY (https://fred.stlouisfed.org/docs/api/api_key.html)"
    return out
