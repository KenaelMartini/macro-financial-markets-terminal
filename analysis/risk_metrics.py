# -*- coding: utf-8 -*-
"""
Risk dashboard: VIX, Fear & Greed, VaR/CVaR — cotations et historiques via IBKR (TWS).
"""

import logging
import re
from typing import Any, Dict, List, Optional

import requests

log = logging.getLogger("terminal.risk")

ALT_FG_URL = "https://api.alternative.me/fng/?limit=1"

_SYM_SAFE = re.compile(r"^[\w^=.\-]{2,40}$", re.I)


def _fg_index() -> Optional[Dict[str, Any]]:
    """Crypto Fear & Greed (alternative.me) — proxy retail, hors IBKR."""
    try:
        r = requests.get(ALT_FG_URL, timeout=12)
        if r.status_code != 200:
            return None
        data = r.json()
        row = (data.get("data") or [{}])[0]
        return {
            "score": int(row["value"]) if row.get("value") is not None else None,
            "rating": row.get("value_classification") or "",
            "timestamp": row.get("timestamp"),
            "source": "alternative.me (crypto F&G)",
        }
    except Exception as e:
        log.debug(f"Fear & Greed fetch: {e}")
        return None


def _sanitize_symbol(sym: str) -> Optional[str]:
    s = (sym or "").strip().upper()
    if not s or not _SYM_SAFE.match(s):
        return None
    return s


def _var_cvar_from_returns(
    rets: List[float], confidence: float, benchmark: str
) -> Optional[Dict[str, Any]]:
    if len(rets) < 30:
        return None
    sorted_rets = sorted(rets)
    idx = max(0, int((1.0 - confidence) * len(sorted_rets)) - 1)
    var_ret = sorted_rets[idx]
    tail = [x for x in sorted_rets if x <= var_ret]
    cvar_ret = sum(tail) / len(tail) if tail else var_ret
    return {
        "benchmark": benchmark,
        "confidence": confidence,
        "observations": len(rets),
        "var_return_pct": round(var_ret * 100, 4),
        "cvar_return_pct": round(cvar_ret * 100, 4),
        "var_daily_pct": round(var_ret * 100, 4),
        "cvar_daily_pct": round(cvar_ret * 100, 4),
        "note": "VaR = quantile des rendements journaliers simples (historique IBKR).",
    }


def _closes_to_returns(closes: List[float]) -> List[float]:
    rets = []
    for i in range(1, len(closes)):
        a, b = closes[i - 1], closes[i]
        if a and abs(a) > 1e-12:
            rets.append((b - a) / a)
    return rets


def _vix_snapshot_ibkr() -> Optional[Dict[str, Any]]:
    from scrapers import ibkr

    if not ibkr.is_connected():
        return None
    for row in ibkr.live_market_data.get("instruments") or []:
        if row.get("symbol") == "^VIX":
            return {
                "price": row.get("price"),
                "change_pct": row.get("change_pct"),
                "source": "ibkr",
            }
    closes = ibkr.fetch_daily_closes("^VIX", days=10)
    if closes and len(closes) >= 2:
        last, prev = closes[-1], closes[-2]
        chg = ((last - prev) / prev * 100) if prev else 0.0
        return {"price": round(last, 2), "change_pct": round(chg, 3), "source": "ibkr"}
    return None


def _historical_var_cvar_ibkr(symbol: str = "SPY") -> Optional[Dict[str, Any]]:
    from scrapers import ibkr

    if not ibkr.is_connected():
        return None
    closes = ibkr.fetch_daily_closes(symbol, days=280)
    if not closes or len(closes) < 31:
        return None
    rets = _closes_to_returns(closes)
    return _var_cvar_from_returns(rets, 0.95, symbol)


def compute_var_cvar_calculator(
    symbol: str,
    portfolio_usd: float,
    confidence: float = 0.95,
    lookback_days: int = 252,
) -> Optional[Dict[str, Any]]:
    """VaR / CVaR historique à partir des closes journaliers IBKR."""
    from scrapers import ibkr

    sym = _sanitize_symbol(symbol)
    if sym is None or portfolio_usd <= 0 or confidence <= 0 or confidence >= 1:
        return None
    if not ibkr.is_connected():
        return None
    closes = ibkr.fetch_daily_closes(sym, max(lookback_days + 40, 80))
    if not closes or len(closes) < 31:
        return None
    span = min(len(closes), lookback_days + 1)
    window = closes[-span:]
    rets = _closes_to_returns(window)
    if len(rets) < 30:
        return None
    base = _var_cvar_from_returns(rets, confidence, sym)
    if not base:
        return None
    var_ret = base["var_return_pct"] / 100.0
    cvar_ret = base["cvar_return_pct"] / 100.0
    var_loss_pct = max(0.0, -var_ret * 100.0)
    cvar_loss_pct = max(0.0, -cvar_ret * 100.0)
    var_usd = round(portfolio_usd * var_loss_pct / 100.0, 2)
    cvar_usd = round(portfolio_usd * cvar_loss_pct / 100.0, 2)
    return {
        "symbol": sym,
        "confidence": confidence,
        "lookback_days": lookback_days,
        "portfolio_usd": portfolio_usd,
        "observations": base["observations"],
        "var_return_pct": base["var_return_pct"],
        "cvar_return_pct": base["cvar_return_pct"],
        "var_loss_pct_1d": round(var_loss_pct, 4),
        "cvar_loss_pct_1d": round(cvar_loss_pct, 4),
        "var_1d_usd": var_usd,
        "cvar_1d_usd": cvar_usd,
        "method": "Historical VaR / CVaR — rendements journaliers simples (IBKR).",
    }


def build_risk_snapshot() -> Dict[str, Any]:
    from scrapers import ibkr

    connected = ibkr.is_connected()
    vix = _vix_snapshot_ibkr() if connected else None
    var_cvar = _historical_var_cvar_ibkr("SPY") if connected else None
    return {
        "vix": vix,
        "fear_greed": _fg_index(),
        "var_cvar": var_cvar,
        "source": "ibkr" if connected else "ibkr_offline",
    }
