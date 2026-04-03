# -*- coding: utf-8 -*-
"""
IBKR (TWS/Gateway) live market data — source unique pour les cotations terminal.
Pas de fallback Yahoo : instruments sans contrat IBKR ou sans droits marché sont ignorés.
"""

import math
import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID
from scrapers import market_data as yf_market

log = logging.getLogger("terminal.ibkr")

try:
    from ib_insync import IB, Forex, Stock, ContFuture, Index

    _ib_available = True
except Exception:
    _ib_available = False
    IB = None  # type: ignore

try:
    from ib_insync import Crypto as _Crypto  # type: ignore
except Exception:
    _Crypto = None  # type: ignore


live_market_data: Dict[str, Any] = {"instruments": [], "last_refresh": ""}
status: Dict[str, Any] = {
    "enabled": _ib_available,
    "connected": False,
    "last_error": "",
    "last_tick_at": "",
    "host": IBKR_HOST,
    "port": IBKR_PORT,
    "client_id": IBKR_CLIENT_ID,
}

_PAIR_CANON = {
    "EURUSD=X": ("EURUSD", "EUR/USD"),
    "GBPUSD=X": ("GBPUSD", "GBP/USD"),
    "JPY=X": ("USDJPY", "USD/JPY"),
    "CHF=X": ("USDCHF", "USD/CHF"),
    "AUDUSD=X": ("AUDUSD", "AUD/USD"),
    "NZDUSD=X": ("NZDUSD", "NZD/USD"),
    "CAD=X": ("USDCAD", "USD/CAD"),
    "EURGBP=X": ("EURGBP", "EUR/GBP"),
    "EURJPY=X": ("EURJPY", "EUR/JPY"),
    "GBPJPY=X": ("GBPJPY", "GBP/JPY"),
    "EURCHF=X": ("EURCHF", "EUR/CHF"),
    "AUDJPY=X": ("AUDJPY", "AUD/JPY"),
    "USDMXN=X": ("USDMXN", "USD/MXN"),
    "USDZAR=X": ("USDZAR", "USD/ZAR"),
    "USDCNH=X": ("USDCNH", "USD/CNH"),
}


def _is_num(x: Any) -> bool:
    try:
        f = float(x)
        return math.isfinite(f)
    except Exception:
        return False


def _safe_connect(ib: "IB", host: str, port: int, client_id: int, timeout: float = 8.0):
    """
    Connect using an explicit event loop to avoid sporadic
    'coroutine ... connectAsync was never awaited' warnings in worker threads.
    """
    # Worker threads on Windows often have no default asyncio loop.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
    return ib.connect(
        host=host,
        port=port,
        clientId=client_id,
        timeout=timeout,
        readonly=True,
    )


def _what_to_show(inst: dict) -> str:
    return "MIDPOINT" if inst.get("asset_class") == "FX" else "TRADES"


def _contract_for(inst: dict):
    sym = inst.get("symbol", "")
    ac = inst.get("asset_class")
    if ac == "FX" and sym in _PAIR_CANON:
        return Forex(_PAIR_CANON[sym][0])
    if sym in {"AAPL", "MSFT", "NVDA", "SPY"}:
        return Stock(sym, "SMART", "USD")
    if sym == "ES=F":
        return ContFuture("ES", "CME")
    if sym == "NQ=F":
        return ContFuture("NQ", "CME")
    if sym == "^VIX":
        return Index("VIX", "CBOE")
    # Dollar index (Yahoo DX-Y.NYB)
    if sym == "DX-Y.NYB":
        return Index("DXY", "ECBOT")
    # US Treasury yields (indices on CBOE / ECBOT)
    if sym == "^TNX":
        return Index("TNX", "ECBOT")
    if sym == "^FVX":
        return Index("FVX", "ECBOT")
    if sym == "^IRX":
        return Index("IRX", "ECBOT")
    # Crypto PAXOS (paper often delayed / entitlement-dependent)
    if sym == "BTC-USD" and _Crypto is not None:
        return _Crypto("BTC", "PAXOS", "USD")
    if sym == "ETH-USD" and _Crypto is not None:
        return _Crypto("ETH", "PAXOS", "USD")
    if sym in {"SOL-USD", "XRP-USD"}:
        return None
    # Indices (best effort SMART / CBOE)
    if sym == "^GSPC":
        return Index("SPX", "CBOE")
    if sym == "^NDX":
        return Index("NDX", "NASDAQ")
    if sym == "^STOXX50E":
        return Index("SX5E", "EUREX")
    if sym == "^N225":
        return Index("N225", "OSE.JPN")
    if sym == "^FTSE":
        return None
    # Commodities
    if sym == "GC=F":
        return ContFuture("GC", "COMEX")
    if sym == "CL=F":
        return ContFuture("CL", "NYMEX")
    if sym == "SI=F":
        return ContFuture("SI", "COMEX")
    if sym == "NG=F":
        return ContFuture("NG", "NYMEX")
    if sym == "HG=F":
        return ContFuture("HG", "COMEX")
    return None


def _canonical_name(inst: dict) -> str:
    sym = inst.get("symbol", "")
    if sym in _PAIR_CANON:
        return _PAIR_CANON[sym][1]
    return inst.get("name", sym)


def _calc_daily_change(ib: "IB", contract, inst: dict) -> Optional[float]:
    try:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="4 D",
            barSizeSetting="1 day",
            whatToShow=_what_to_show(inst),
            useRTH=False,
        )
        closes = [float(b.close) for b in bars if _is_num(getattr(b, "close", None))]
        if len(closes) < 2:
            return None
        prev_close = closes[-2]
        last_close = closes[-1]
        if not _is_num(prev_close) or prev_close == 0:
            return None
        return (last_close - prev_close) / prev_close * 100.0
    except Exception:
        return None


def _calc_history(ib: "IB", contract, inst: dict) -> List[float]:
    try:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="2 D",
            barSizeSetting="30 mins",
            whatToShow=_what_to_show(inst),
            useRTH=False,
        )
        vals = [float(b.close) for b in bars if _is_num(getattr(b, "close", None))]
        return [round(v, 6) for v in vals[-48:]]
    except Exception:
        return []


def _extract_price(tk) -> Optional[float]:
    bid = getattr(tk, "bid", None)
    ask = getattr(tk, "ask", None)
    if _is_num(bid) and _is_num(ask) and float(bid) > 0 and float(ask) > 0:
        return (float(bid) + float(ask)) / 2.0
    for v in (
        getattr(tk, "marketPrice", lambda: None)(),
        getattr(tk, "last", None),
        getattr(tk, "close", None),
        getattr(tk, "bid", None),
        getattr(tk, "ask", None),
    ):
        if _is_num(v):
            return float(v)
    return None


def _last_close_from_daily_hist(ib: "IB", contract, inst: dict) -> Optional[float]:
    """Si le flux live n’a pas encore de prix (droits / délai), dernier close journalier IBKR."""
    try:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="10 D",
            barSizeSetting="1 day",
            whatToShow=_what_to_show(inst),
            useRTH=False,
        )
        if not bars:
            return None
        c = getattr(bars[-1], "close", None)
        return float(c) if _is_num(c) else None
    except Exception:
        return None


def _candle_request_spec(period: str, interval: str) -> Tuple[str, str]:
    """Normalize UI period/interval to IBKR duration + bar size."""
    bar_map = {
        "1h": "1 hour",
        "4h": "4 hours",
        "8h": "8 hours",
        "1d": "1 day",
    }
    intraday_dur_map = {
        "1h": {
            "1mo": "30 D",
            "3mo": "90 D",
            "6mo": "180 D",
            "9mo": "270 D",
            "1y": "1 Y",
            "2y": "2 Y",
            "5y": "2 Y",
            "10y": "2 Y",
            "max": "2 Y",
        },
        "4h": {
            "1mo": "30 D",
            "3mo": "90 D",
            "6mo": "180 D",
            "9mo": "270 D",
            "1y": "1 Y",
            "2y": "2 Y",
            "5y": "5 Y",
            "10y": "5 Y",
            "max": "5 Y",
        },
        "8h": {
            "1mo": "30 D",
            "3mo": "90 D",
            "6mo": "180 D",
            "9mo": "270 D",
            "1y": "1 Y",
            "2y": "2 Y",
            "5y": "5 Y",
            "10y": "5 Y",
            "max": "5 Y",
        },
    }
    daily_dur_map = {
        "1mo": "1 M",
        "3mo": "3 M",
        "6mo": "6 M",
        "9mo": "9 M",
        "1y": "1 Y",
        "2y": "2 Y",
        "5y": "5 Y",
        "10y": "10 Y",
        "max": "20 Y",
    }
    iv = (interval or "1d").strip().lower()
    p = (period or "6mo").strip().lower()
    bar_size = bar_map.get(iv, "1 day")
    if iv == "1d":
        return daily_dur_map.get(p, "1 Y"), bar_size
    if iv in intraday_dur_map:
        return intraday_dur_map[iv].get(p, "180 D"), bar_size
    return "1 Y", "1 day"


def _serialize_bar_time(ts: Any, interval: str):
    """Daily bars -> YYYY-MM-DD ; intraday bars -> unix utc seconds."""
    iv = (interval or "1d").strip().lower()
    if not hasattr(ts, "strftime"):
        return str(ts)[:10] if iv == "1d" else None
    if iv == "1d":
        return ts.strftime("%Y-%m-%d")
    if getattr(ts, "tzinfo", None) is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return int(ts.astimezone(timezone.utc).timestamp())


def fetch_ohlc_candles(
    symbol: str, period: str = "6mo", interval: str = "1d"
) -> Optional[Dict[str, Any]]:
    if not _ib_available:
        return None
    inst = next((x for x in yf_market.INSTRUMENTS if x.get("symbol") == symbol), None)
    if not inst:
        return None
    contract = _contract_for(inst)
    if contract is None:
        return None
    duration, bar_size = _candle_request_spec(period, interval)
    ib = IB()
    try:
        _safe_connect(ib, IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID + 1, timeout=8)
        q = ib.qualifyContracts(contract)
        if not q:
            return None
        bars = ib.reqHistoricalData(
            q[0],
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=_what_to_show(inst),
            useRTH=False,
        )
        candles = []
        for b in bars or []:
            try:
                ts = getattr(b, "date", None)
                tstr = _serialize_bar_time(ts, interval)
                if tstr is None:
                    continue
                o, h, l, c = float(b.open), float(b.high), float(b.low), float(b.close)
                if not (_is_num(o) and _is_num(h) and _is_num(l) and _is_num(c)):
                    continue
                candles.append(
                    {
                        "time": tstr,
                        "open": round(o, 6),
                        "high": round(max(o, h, l, c), 6),
                        "low": round(min(o, h, l, c), 6),
                        "close": round(c, 6),
                    }
                )
            except Exception:
                continue
        seen = set()
        uniq = []
        for x in candles:
            if x["time"] in seen:
                continue
            seen.add(x["time"])
            uniq.append(x)
        uniq.sort(key=lambda x: x["time"])
        return {
            "symbol": symbol,
            "name": _canonical_name(inst),
            "interval": interval,
            "source": "ibkr",
            "candles": uniq,
        }
    except Exception:
        return None
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass


def fetch_daily_closes(symbol: str, days: int = 260) -> Optional[List[float]]:
    """Closes journaliers (ordre chronologique) pour VaR / CVaR — même résolution de contrat que les bougies."""
    if not _ib_available or days < 30:
        return None
    inst = next((x for x in yf_market.INSTRUMENTS if x.get("symbol") == symbol), None)
    if not inst:
        return None
    contract = _contract_for(inst)
    if contract is None:
        return None
    if days <= 365:
        duration_str = f"{min(max(days + 20, 50), 365)} D"
    elif days <= 730:
        duration_str = "2 Y"
    else:
        duration_str = "5 Y"
    ib = IB()
    try:
        _safe_connect(ib, IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID + 4, timeout=12)
        q = ib.qualifyContracts(contract)
        if not q:
            return None
        bars = ib.reqHistoricalData(
            q[0],
            endDateTime="",
            durationStr=duration_str,
            barSizeSetting="1 day",
            whatToShow=_what_to_show(inst),
            useRTH=False,
        )
        out: List[float] = []
        for b in bars or []:
            c = getattr(b, "close", None)
            if _is_num(c):
                out.append(float(c))
        return out if len(out) >= 30 else None
    except Exception:
        return None
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass


def get_status() -> Dict[str, Any]:
    return dict(status)


def is_connected() -> bool:
    return bool(status.get("connected"))


def refresh_once():
    """Single IBKR poll cycle."""
    global live_market_data
    if not _ib_available:
        status["last_error"] = "ib_insync not installed"
        return
    ib = IB()
    try:
        _safe_connect(ib, IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, timeout=8)
        status["connected"] = True
        status["last_error"] = ""
        out_rows = []
        for inst in yf_market.INSTRUMENTS:
            sym = inst.get("symbol", "")
            contract = _contract_for(inst)
            if contract is None:
                continue
            try:
                q = ib.qualifyContracts(contract)
                if not q:
                    continue
                c = q[0]
                tk = ib.reqMktData(c, "", False, False)
                ib.sleep(0.45)
                px = _extract_price(tk)
                if px is None:
                    px = _last_close_from_daily_hist(ib, c, inst)
                chg = _calc_daily_change(ib, c, inst)
                hist = _calc_history(ib, c, inst)
                if px is None:
                    continue
                out_rows.append(
                    {
                        "symbol": sym,
                        "name": _canonical_name(inst),
                        "asset_class": inst.get("asset_class", ""),
                        "price": round(float(px), 6),
                        "change_pct": round(float(chg if chg is not None else 0.0), 4),
                        "history": hist or [round(float(px), 6)],
                    }
                )
                status["last_tick_at"] = datetime.now(timezone.utc).isoformat()
            except Exception:
                continue
        live_market_data = {
            "instruments": out_rows,
            "last_refresh": datetime.now(timezone.utc).isoformat(),
            "source": "ibkr",
        }
        try:
            from storage.sqlite_store import persist_market_snapshot

            persist_market_snapshot(dict(live_market_data))
        except Exception as e:
            log.debug("market persist skipped: %s", e)
    except Exception as e:
        status["connected"] = False
        status["last_error"] = str(e)
        log.warning(f"IBKR connect/refresh error: {e}")
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass


def refresh_loop():
    if not _ib_available:
        status["last_error"] = "ib_insync not installed"
        return
    while True:
        refresh_once()
        time.sleep(35)
