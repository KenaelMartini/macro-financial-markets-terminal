# -*- coding: utf-8 -*-
"""
All API REST endpoints + WebSocket for the terminal.
"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from config import (
    BANK_META,
    BANK_ORDER,
    CB_DIR,
    ENABLE_AUTH,
    TEMPLATES_DIR,
    TERMINAL_API_KEY,
    get_paths_health,
)
from loaders import (
    load_cb_states,
    load_cb_events,
    load_calendar_file,
    read_jsonl_tail_filtered,
)
from analysis.cb_tone_live import enrich_cb_state
from scrapers import news, cb_poller, calendar, ibkr
from analysis.signals import generate_signals
from analysis.pricein import analyze_pricein
from analysis.reports import generate_brief
from analysis.risk_metrics import build_risk_snapshot, compute_var_cvar_calculator
from alerts.store import get_alerts, add_alert, load as load_alerts
from storage.sqlite_store import (
    db_stats,
    fetch_history_calendar,
    fetch_history_cb_snapshots,
    fetch_history_news,
    fetch_nlp_history,
)
from workers.supervisor import workers_status_snapshot

router = APIRouter()

_ws_clients: list = []

_ALLOWED_INTERVALS = {"1h", "4h", "8h", "1d"}
_ALLOWED_PERIODS = {"1mo", "3mo", "6mo", "9mo", "1y", "2y", "5y", "10y", "max"}


def _live_market_payload() -> dict:
    """Cotations live uniquement via IBKR (structure toujours valide si TWS connecté)."""
    if ibkr.is_connected():
        d = dict(ibkr.live_market_data)
        d.setdefault("instruments", [])
        d["source"] = "ibkr"
        return d
    return {
        "instruments": [],
        "last_refresh": "",
        "source": "ibkr",
        "ibkr_disconnected": True,
        "ibkr_error": (ibkr.get_status() or {}).get("last_error", ""),
    }


def _get_calendar() -> list:
    """Live calendar or normalized file fallback (with Investing actual merge)."""
    if calendar.live_calendar:
        return calendar.live_calendar
    raw = load_calendar_file()
    return calendar.finalize_calendar_events(raw)


def _get_cb_states() -> dict:
    if cb_poller.live_states:
        return cb_poller.live_states
    return load_cb_states()


def _get_cb_states_for_api() -> dict:
    """États banques + analyse lexicale sur le dernier titre du poll (pas le marché)."""
    raw = dict(_get_cb_states())
    safe_items = list(raw.items())
    return {bid: enrich_cb_state(bid, dict(st)) for bid, st in safe_items}


# ── HTML ──────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def root():
    html_path = TEMPLATES_DIR / "index.html"
    if not html_path.exists():
        return HTMLResponse("<h1>index.html not found</h1>", status_code=500)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ── REST API: Core ────────────────────────────────────────────────

@router.get("/api/cb-states")
async def api_cb_states():
    return _get_cb_states_for_api()


@router.get("/api/news")
async def api_news(limit: int = 1500):
    articles = news.live_articles[:limit]
    return {
        "articles": articles,
        "total": len(articles),
        "last_refresh": news.last_refresh,
    }


@router.get("/api/calendar")
async def api_calendar():
    return _get_calendar()


@router.get("/api/cb-events")
async def api_cb_events():
    return load_cb_events()


@router.get("/api/cb/{bank_id}/history")
async def api_cb_history(bank_id: str, limit: int = 50):
    """Historique filtré (sans entrées de démo évidentes dans les JSONL)."""
    history_dir = CB_DIR / "data" / "history"
    for bank_dir in history_dir.iterdir() if history_dir.exists() else []:
        normalized = bank_dir.name.lower().replace(" ", "_")
        if normalized == bank_id or bank_dir.name.lower() == bank_id:
            events_file = bank_dir / "events.jsonl"
            return read_jsonl_tail_filtered(events_file, n=limit, scan_last_lines=1200)
    return []


# ── REST API: Markets ─────────────────────────────────────────────

@router.get("/api/markets")
async def api_markets():
    return _live_market_payload()


@router.get("/api/markets/candles")
async def api_market_candles(
    symbol: str,
    period: str = "6mo",
    interval: str = "1d",
    source: str = "auto",
):
    """Historique OHLC uniquement via IBKR (TWS doit être connecté)."""
    del source  # conservé pour compat URL ; source unique = IBKR
    interval = (interval or "1d").strip().lower()
    period = (period or "6mo").strip().lower()
    if interval not in _ALLOWED_INTERVALS:
        return {"error": "bad_interval", "detail": "interval must be one of 1h,4h,8h,1d"}
    if period not in _ALLOWED_PERIODS:
        return {"error": "bad_period", "detail": "period must be one of 1mo,3mo,6mo,9mo,1y,2y,5y,10y,max"}
    if not ibkr.is_connected():
        return {
            "error": "ibkr_disconnected",
            "symbol": symbol,
            "candles": [],
            "detail": (ibkr.get_status() or {}).get("last_error", ""),
        }
    data = await asyncio.to_thread(
        ibkr.fetch_ohlc_candles, symbol, period=period, interval=interval
    )
    if not data:
        return {"error": "no_data", "symbol": symbol, "candles": []}
    return data


@router.get("/api/markets/candles/last")
async def api_market_candles_last(
    symbol: str,
    interval: str = "1h",
):
    """Retourne les 2 dernières bougies pour refresh léger client."""
    interval = (interval or "1h").strip().lower()
    if interval not in _ALLOWED_INTERVALS:
        return {"error": "bad_interval", "detail": "interval must be one of 1h,4h,8h,1d"}
    if not ibkr.is_connected():
        return {
            "error": "ibkr_disconnected",
            "symbol": symbol,
            "candles": [],
            "detail": (ibkr.get_status() or {}).get("last_error", ""),
        }
    period_hint = "1mo" if interval != "1d" else "3mo"
    data = await asyncio.to_thread(
        ibkr.fetch_ohlc_candles, symbol, period=period_hint, interval=interval
    )
    if not data or not data.get("candles"):
        return {"error": "no_data", "symbol": symbol, "candles": []}
    return {
        "symbol": data.get("symbol", symbol),
        "name": data.get("name", symbol),
        "interval": interval,
        "source": "ibkr",
        "candles": (data.get("candles") or [])[-2:],
    }


# ── REST API: Risk (VIX, VaR, Fear&Greed) ─────────────────────────

@router.get("/api/risk")
async def api_risk():
    return await asyncio.to_thread(build_risk_snapshot)


class VarCalcBody(BaseModel):
    symbol: str = "SPY"
    portfolio_usd: float = 100_000.0
    confidence: float = 0.95
    lookback_days: int = 252


@router.post("/api/risk/var-calc")
async def api_risk_var_calc(body: VarCalcBody):
    """Calculateur VaR / CVaR historique (1 jour) sur historique IBKR."""
    if body.confidence <= 0.5 or body.confidence >= 1.0:
        return {"error": "bad_confidence", "detail": "confidence must be between 0.5 and 1.0 (e.g. 0.95)"}
    if body.lookback_days < 30 or body.lookback_days > 2000:
        return {"error": "bad_lookback", "detail": "lookback_days 30..2000"}
    if body.portfolio_usd <= 0:
        return {"error": "bad_portfolio", "detail": "portfolio_usd must be > 0"}
    r = await asyncio.to_thread(
        compute_var_cvar_calculator,
        body.symbol.strip(),
        float(body.portfolio_usd),
        float(body.confidence),
        int(body.lookback_days),
    )
    if not r:
        return {
            "error": "compute_failed",
            "detail": "TWS déconnecté, symbole inconnu, ou pas assez d’historique IBKR.",
        }
    return r


# ── REST API: Signals ─────────────────────────────────────────────

@router.get("/api/signals")
async def api_signals():
    signals = generate_signals(
        news.live_articles,
        _live_market_payload(),
    )
    return {"signals": signals}


# ── REST API: Price-In ────────────────────────────────────────────

@router.get("/api/pricein")
async def api_pricein():
    mkt = _live_market_payload()
    signals = generate_signals(news.live_articles, mkt)
    result = analyze_pricein(mkt, signals)
    return result


# ── REST API: Intel ───────────────────────────────────────────────

@router.get("/api/intel/brief")
async def api_intel_brief():
    return generate_brief(news.live_articles, _get_cb_states(), _get_calendar())


@router.post("/api/intel/generate")
async def api_intel_generate():
    return generate_brief(news.live_articles, _get_cb_states(), _get_calendar())


# ── REST API: Alerts ──────────────────────────────────────────────

class AlertCreate(BaseModel):
    type: str
    bank: Optional[str] = ""
    value: Optional[str] = ""


@router.get("/api/alerts")
async def api_alerts():
    return {"alerts": get_alerts()}


@router.post("/api/alerts")
async def api_alerts_create(alert: AlertCreate):
    alerts = add_alert(alert.type, alert.bank or "", alert.value or "")
    return {"alerts": alerts}


# ── REST API: Status ──────────────────────────────────────────────

@router.get("/api/status")
async def api_status():
    states = dict(_get_cb_states())
    cal = _get_calendar()
    events = dict(load_cb_events())
    mkt = _live_market_payload()
    return {
        "banks_monitored": len(states),
        "banks_live": len(cb_poller.live_states),
        "total_articles": len(news.live_articles),
        "feeds_active": len(news.feeds),
        "calendar_events": len(cal),
        "calendar_live": bool(calendar.live_calendar),
        "cb_events": sum(len(v) for v in events.values()),
        "market_instruments": len(mkt.get("instruments", [])),
        "markets_source": "ibkr" if ibkr.is_connected() else "ibkr_offline",
        "ibkr_connected": ibkr.is_connected(),
        "ibkr_last_tick_at": ibkr.get_status().get("last_tick_at", ""),
        "ibkr_last_error": ibkr.get_status().get("last_error", ""),
        "last_news_refresh": news.last_refresh,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "paths": get_paths_health(),
        "workers": workers_status_snapshot(),
        "sqlite": db_stats(),
    }


@router.get("/api/history/news")
async def api_history_news(since: str = "1970-01-01T00:00:00+00:00", limit: int = 500):
    rows = await asyncio.to_thread(fetch_history_news, since, min(limit, 2000))
    return {"articles": rows, "count": len(rows), "since": since}


@router.get("/api/history/calendar")
async def api_history_calendar(since: str = "1970-01-01", limit: int = 400):
    rows = await asyncio.to_thread(fetch_history_calendar, since, min(limit, 2000))
    return {"events": rows, "count": len(rows), "since": since}


@router.get("/api/history/cb/{bank_id}")
async def api_history_cb_snapshots(bank_id: str, limit: int = 80):
    rows = await asyncio.to_thread(fetch_history_cb_snapshots, bank_id.lower(), min(limit, 500))
    return {"snapshots": rows, "count": len(rows), "bank_id": bank_id.lower()}


@router.get("/api/history/nlp/{bank_id}")
async def api_history_nlp(bank_id: str, limit: int = 80):
    rows = await asyncio.to_thread(fetch_nlp_history, bank_id.lower(), min(limit, 500))
    return {"history": rows, "count": len(rows), "bank_id": bank_id.lower()}


@router.get("/api/yields/curve")
async def api_yields_curve():
    from analysis.yield_curve import build_yield_curve_payload

    return await asyncio.to_thread(build_yield_curve_payload)


@router.get("/api/yields/fedfunds-implied")
async def api_fedfunds_implied():
    from analysis.fed_funds_implied import build_fedfunds_implied_payload

    return await asyncio.to_thread(build_fedfunds_implied_payload, mkt_snapshot=_live_market_payload())


@router.get("/api/analytics/cb-market-correlation")
async def api_cb_market_correlation(bank_id: str = "fed", lookback_rows: int = 40):
    from analysis.cb_market_link import cb_tone_vs_spy_correlation

    return await asyncio.to_thread(cb_tone_vs_spy_correlation, bank_id.lower(), lookback_rows)


@router.get("/api/intel/session-report")
async def api_intel_session_report():
    from analysis.reports import generate_session_report

    return await asyncio.to_thread(
        generate_session_report,
        news.live_articles,
        _get_cb_states(),
        _get_calendar(),
        _live_market_payload(),
    )


# ── WebSocket ─────────────────────────────────────────────────────

@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    if ENABLE_AUTH and TERMINAL_API_KEY:
        if ws.query_params.get("api_key") != TERMINAL_API_KEY:
            await ws.close(code=4401)
            return
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            await ws.send_json({
                "type": "heartbeat",
                "cb_states": _get_cb_states_for_api(),
                "article_count": len(news.live_articles),
                "market_data": _live_market_payload(),
                "ibkr_status": ibkr.get_status(),
                "server_time": datetime.now(timezone.utc).isoformat(),
            })
            await asyncio.sleep(15)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)
