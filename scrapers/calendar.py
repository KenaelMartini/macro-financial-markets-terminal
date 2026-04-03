# -*- coding: utf-8 -*-
"""
Live economic calendar: ForexFactory JSON + enrichment of « actual » (and gaps)
from Investing.com HTML calendar (FF mirror JSON has no actual field).
"""

import re
import time
import logging
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from html import unescape
from collections import defaultdict
from typing import List, Any, Dict, Tuple, Optional

import requests

from config import (
    CALENDAR_REFRESH_SEC,
    FF_CALENDAR_URL,
    FINNHUB_API_KEY,
    HTTP_HEADERS,
)
from loaders import load_calendar_file

log = logging.getLogger("terminal.calendar")

# ── In-memory state ──────────────────────────────────────────────
live_calendar: List[dict] = []

# Cache Investing merge for API fallback (avoid POST on every /api/calendar)
_enriched_fallback_cache: Optional[List[dict]] = None
_enriched_fallback_cache_at: float = 0.0
_ENRICH_CACHE_TTL_SEC = 600.0

_HTML_TAG = re.compile(r"<[^>]+>")

INVESTING_CAL_HEADERS = {
    "User-Agent": HTTP_HEADERS.get(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.investing.com",
    "Referer": "https://www.investing.com/economic-calendar/",
}

INVESTING_CAL_URL = (
    "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
)

# Finnhub uses ISO country codes; FF « country » is usually the quote currency (EUR, USD, …).
_FN_COUNTRY_TO_CCY = {
    "US": "USD",
    "EU": "EUR",
    "EMU": "EUR",
    "DE": "EUR",
    "FR": "EUR",
    "IT": "EUR",
    "ES": "EUR",
    "NL": "EUR",
    "BE": "EUR",
    "AT": "EUR",
    "IE": "EUR",
    "PT": "EUR",
    "GR": "EUR",
    "GB": "GBP",
    "UK": "GBP",
    "JP": "JPY",
    "AU": "AUD",
    "NZ": "NZD",
    "CA": "CAD",
    "CH": "CHF",
    "CN": "CNY",
    "HK": "HKD",
    "SG": "SGD",
    "IN": "INR",
    "KR": "KRW",
    "SE": "SEK",
    "NO": "NOK",
    "RU": "RUB",
    "BR": "BRL",
    "MX": "MXN",
    "ZA": "ZAR",
}


def _strip_val(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    s = _HTML_TAG.sub("", s)
    return s.strip()


def normalize_event(ev: Dict[str, Any]) -> Dict[str, Any]:
    """Map various JSON keys to forecast, previous, actual."""
    if not isinstance(ev, dict):
        return ev
    out = dict(ev)
    f = (
        out.get("forecast")
        or out.get("Forecast")
        or out.get("consensus")
        or out.get("expected")
    )
    p = out.get("previous") or out.get("Previous") or out.get("prior")
    a = (
        out.get("actual")
        or out.get("Actual")
        or out.get("result")
        or out.get("release")
    )
    out["forecast"] = _strip_val(f)
    out["previous"] = _strip_val(p)
    out["actual"] = _strip_val(a)
    return out


def _normalize_list(events: List[dict]) -> List[dict]:
    return [normalize_event(e) for e in events if isinstance(e, dict)]


def _ff_event_date(iso: str) -> Optional[date]:
    if not iso or not isinstance(iso, str):
        return None
    s = iso.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        return dt.date()
    except ValueError:
        return None


def _norm_cal_title(s: str) -> str:
    t = (s or "").lower()
    t = t.replace("m/m", "mom").replace("q/q", "qoq").replace("y/y", "yoy")
    t = t.replace("(mom)", "mom").replace("(qoq)", "qoq").replace("(yoy)", "yoy")
    t = re.sub(r"\s*\([^)]*\)", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


def _strip_cell_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return unescape(s).replace("\xa0", " ").strip()


def _parse_investing_calendar_html(html: str) -> List[Dict[str, Any]]:
    """Parse table rows from getCalendarFilteredData JSON 'data' HTML."""
    if not html:
        return []
    parts = re.split(r'<tr id="eventRowId_\d+"', html)
    rows: List[Dict[str, Any]] = []
    for chunk in parts[1:]:
        mdt = re.search(r'data-event-datetime="([^"]+)"', chunk)
        if not mdt:
            continue
        dt_raw = mdt.group(1).strip()
        d_part = dt_raw.split()[0] if dt_raw else ""
        try:
            y, mo, da = (int(x) for x in d_part.split("/"))
            d = date(y, mo, da)
        except (ValueError, TypeError):
            continue

        mc = re.search(r'flagCur[^>]*>.*?</span>\s*([A-Z]{3})', chunk, re.DOTALL)
        ccy = mc.group(1) if mc else ""

        mt = re.search(
            r'<td class="left event"[^>]*>.*?<a[^>]*>(.*?)</a>', chunk, re.DOTALL
        )
        title_raw = _strip_cell_html(mt.group(1) if mt else "")
        if not title_raw or not ccy:
            continue

        def cell(pat: str) -> str:
            mm = re.search(pat, chunk)
            if not mm:
                return ""
            return _strip_cell_html(mm.group(1))

        rows.append(
            {
                "d": d,
                "ccy": ccy,
                "title": title_raw,
                "title_n": _norm_cal_title(title_raw),
                "actual": cell(r'id="eventActual_\d+">([^<]*)'),
                "forecast": cell(r'id="eventForecast_\d+">([^<]*)'),
                "previous": cell(r'id="eventPrevious_\d+">(?:<span[^>]*>)?([^<]*)'),
            }
        )
    return rows


def _dedupe_aux_calendar_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[Tuple[date, str, str], Dict[str, Any]] = {}
    for row in rows:
        key = (row["d"], row["ccy"], row["title_n"])
        cur = best.get(key)
        if cur is None:
            best[key] = row
            continue
        if row.get("actual") and not cur.get("actual"):
            best[key] = row
    return list(best.values())


def _fetch_finnhub_calendar(w0: date, w1: date) -> List[Dict[str, Any]]:
    if not FINNHUB_API_KEY:
        return []
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/calendar/economic",
            params={
                "from": w0.isoformat(),
                "to": w1.isoformat(),
                "token": FINNHUB_API_KEY,
            },
            timeout=22,
        )
        if r.status_code != 200:
            log.warning(f"Finnhub calendar HTTP {r.status_code}")
            return []
        j = r.json()
        evs = j.get("economicCalendar")
        if not isinstance(evs, list):
            return []
        rows: List[Dict[str, Any]] = []
        for e in evs:
            t = str(e.get("time") or "")
            if len(t) < 10:
                continue
            try:
                day = date.fromisoformat(t[:10])
            except ValueError:
                continue
            fn_c = str(e.get("country") or "").strip().upper()
            ccy = _FN_COUNTRY_TO_CCY.get(fn_c)
            if not ccy:
                continue
            title = str(e.get("event") or "").strip()
            if not title:
                continue

            def fval(x: Any) -> str:
                if x is None:
                    return ""
                if isinstance(x, (int, float)):
                    return str(x)
                return str(x).strip()

            rows.append(
                {
                    "d": day,
                    "ccy": ccy,
                    "title": title,
                    "title_n": _norm_cal_title(title),
                    "actual": fval(e.get("actual")),
                    "forecast": fval(e.get("estimate")),
                    "previous": fval(e.get("prev")),
                }
            )
        log.info(f"Finnhub calendar: {len(rows)} rows for {w0} .. {w1}")
        return rows
    except Exception as e:
        log.warning(f"Finnhub calendar error: {e}")
        return []


def _fetch_investing_for_range(w0: date, w1: date) -> List[Dict[str, Any]]:
    """
    One POST per call. Investing caps ~200 rows; keep (w1-w0) close to the FF « this week » span.
    """
    try:
        resp = requests.post(
            INVESTING_CAL_URL,
            data={
                "dateFrom": w0.strftime("%Y-%m-%d"),
                "dateTo": w1.strftime("%Y-%m-%d"),
                "timeZone": 8,
                "timeFilter": "timeRemain",
                "currentTab": "custom",
                "limit_from": 0,
            },
            headers=INVESTING_CAL_HEADERS,
            timeout=25,
        )
        if resp.status_code == 429:
            log.warning("Investing calendar rate-limited (429); skip enrichment this cycle")
            return []
        if resp.status_code != 200:
            log.warning(f"Investing calendar HTTP {resp.status_code}")
            return []
        data = resp.json()
        html = data.get("data") if isinstance(data, dict) else None
        if not html or not isinstance(html, str):
            return []
        rows = _parse_investing_calendar_html(html)
        log.info(f"Investing calendar: {len(rows)} rows for {w0} .. {w1}")
        return rows
    except Exception as e:
        log.warning(f"Investing calendar fetch error: {e}")
        return []


def _enrich_events_with_investing(events: List[dict]) -> List[dict]:
    ds = []
    for ev in events:
        d = _ff_event_date(str(ev.get("date") or ""))
        if d:
            ds.append(d)
    if not ds:
        return events
    w0 = min(ds) - timedelta(days=1)
    w1 = max(ds) + timedelta(days=1)
    if (w1 - w0).days > 16:
        t = date.today()
        w0, w1 = t - timedelta(days=7), t + timedelta(days=10)
    inv = _dedupe_aux_calendar_rows(
        _fetch_finnhub_calendar(w0, w1) + _fetch_investing_for_range(w0, w1)
    )
    if not inv:
        return events

    by_key: Dict[Tuple[str, date], List[Dict[str, Any]]] = defaultdict(list)
    for row in inv:
        by_key[(row["ccy"], row["d"])].append(row)

    filled = 0
    for ev in events:
        ff_date = _ff_event_date(str(ev.get("date") or ""))
        ff_ccy = (str(ev.get("country") or "")).upper().strip()
        ff_title = str(ev.get("title") or "").strip()
        if not ff_date or not ff_ccy or not ff_title:
            continue
        nff = _norm_cal_title(ff_title)
        candidates = by_key.get((ff_ccy, ff_date), [])
        if not candidates:
            continue
        best = None
        best_score = 0.0
        for row in candidates:
            ninv = row["title_n"]
            ratio = SequenceMatcher(None, nff, ninv).ratio()
            if nff in ninv or ninv in nff:
                ratio = max(ratio, 0.82)
            if ratio > best_score:
                best_score = ratio
                best = row
        if best is None or best_score < 0.48:
            continue
        if best.get("actual") and not (str(ev.get("actual") or "").strip()):
            ev["actual"] = best["actual"]
            filled += 1
        if best.get("forecast") and not (str(ev.get("forecast") or "").strip()):
            ev["forecast"] = best["forecast"]
        if best.get("previous") and not (str(ev.get("previous") or "").strip()):
            ev["previous"] = best["previous"]

    if filled:
        log.info(
            f"Calendar: filled actual on {filled} events "
            "(Finnhub key / Investing.com when available)"
        )
    return events


def _finalize_calendar(raw: List[dict]) -> List[dict]:
    base = _normalize_list(raw)
    merged = _enrich_events_with_investing(base)
    now = datetime.now(timezone.utc)
    upcoming = []
    recent_past = []
    for ev in merged:
        d = str(ev.get("date") or "").strip()
        if not d:
            continue
        try:
            ts = datetime.fromisoformat(d.replace("Z", "+00:00"))
        except Exception:
            continue
        if ts >= now - timedelta(hours=6):
            upcoming.append(ev)
        elif ts >= now - timedelta(days=2):
            recent_past.append(ev)
    upcoming.sort(key=lambda x: str(x.get("date") or ""))
    recent_past.sort(key=lambda x: str(x.get("date") or ""))
    # Priorité aux futurs. On garde un petit tampon de passé récent pour contexte.
    out = upcoming + recent_past
    return out if out else merged


def _fetch() -> List[dict]:
    """Fetch FF JSON and merge actuals from Investing."""
    try:
        resp = requests.get(FF_CALENDAR_URL, headers=HTTP_HEADERS, timeout=15)
        if resp.status_code != 200:
            log.warning(f"FF calendar HTTP {resp.status_code}")
            return []
        data = resp.json()
        if isinstance(data, list):
            return _finalize_calendar(data)
        return []
    except Exception as e:
        log.warning(f"FF calendar fetch error: {e}")
        return []


def finalize_calendar_events(raw: List[Any]) -> List[dict]:
    """API fallback: normalize + merge Investing « actual » (cached briefly)."""
    global _enriched_fallback_cache, _enriched_fallback_cache_at
    rows = [e for e in raw if isinstance(e, dict)]
    if not rows:
        return []
    now = time.time()
    if (
        _enriched_fallback_cache is not None
        and (now - _enriched_fallback_cache_at) < _ENRICH_CACHE_TTL_SEC
    ):
        return _enriched_fallback_cache
    merged = _finalize_calendar(rows)
    _enriched_fallback_cache = merged
    _enriched_fallback_cache_at = now
    return merged


def refresh_once():
    """Single fetch cycle (supervisor)."""
    global live_calendar, _enriched_fallback_cache
    events = _fetch()
    if events:
        live_calendar = events
        _enriched_fallback_cache = None
        log.info(f"Calendar refresh: {len(events)} events this week")
        try:
            from storage.sqlite_store import persist_after_calendar

            persist_after_calendar(live_calendar)
        except Exception as e:
            log.debug("calendar persist skipped: %s", e)
    elif not live_calendar:
        stale = load_calendar_file()
        if stale:
            live_calendar = _finalize_calendar(stale)
            if live_calendar:
                log.info(
                    f"Calendar: loaded {len(live_calendar)} events "
                    "from stale file + enrichment (fallback)"
                )
                try:
                    from storage.sqlite_store import persist_after_calendar

                    persist_after_calendar(live_calendar)
                except Exception as e:
                    log.debug("calendar persist skipped: %s", e)


def refresh_loop():
    """Background thread: fetch calendar every CALENDAR_REFRESH_SEC."""
    while True:
        try:
            refresh_once()
        except Exception as e:
            log.error(f"Calendar refresh error: {e}")
        time.sleep(CALENDAR_REFRESH_SEC)
