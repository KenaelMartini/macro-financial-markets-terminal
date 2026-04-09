# -*- coding: utf-8 -*-
"""
Fed Funds implicite — V1 : proxy depuis taux très court IBKR / cash si présents.
Les contrats FF futurs (ZQ) peuvent être ajoutés quand symboles IBKR sont homologués.
Forme documentée pour futures : implied_avg_rate ≈ 100 - future_price (points).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def implied_from_future_price(price: float) -> float:
    """Convention courante FF futures (index-style) : 100 - prix."""
    return round(100.0 - float(price), 4)


def _find_price(instruments: List[dict], *substrings: str) -> Optional[float]:
    for inst in instruments or []:
        sym = str(inst.get("symbol") or "")
        name = str(inst.get("name") or "").lower()
        blob = sym + " " + name
        if any(s.lower() in blob.lower() for s in substrings):
            p = inst.get("price")
            try:
                return float(p)
            except Exception:
                continue
    return None


def build_fedfunds_implied_payload(mkt_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    inst = mkt_snapshot.get("instruments") or []
    # ^IRX = 13-week T-bill proxy court terme
    irx = _find_price(inst, "^IRX", "IRX", "13 week")
    tnx = _find_price(inst, "^TNX", "TNX", "10 year")

    implied_short: Optional[float] = None
    method = "none"
    if irx is not None:
        implied_short = round(irx, 4)
        method = "irx_yield_pct_proxy"
    elif tnx is not None:
        implied_short = round(tnx * 0.05, 4)
        method = "tnx_scaled_fallback"

    return {
        "schema_version": 1,
        "as_of_utc": now,
        "method": method,
        "implied_policy_rate_pct": implied_short,
        "future_formula_note": "Pour contrat FF type ZQ : implied_avg_rate = 100 - future_price",
        "ibkr_disconnected": bool(mkt_snapshot.get("ibkr_disconnected")),
    }
