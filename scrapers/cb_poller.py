# -*- coding: utf-8 -*-
"""
Live central bank poller -- imports cb_sources to fetch latest metadata.
Runs as a background thread, polling every CB_POLL_SEC.
"""

import re
import sys
import time
import logging
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests

from config import (
    CB_DIR, HTTP_HEADERS, BANK_META,
    CB_POLL_SEC, CB_BANK_TIMEOUT, RSS_FALLBACKS,
)
from scrapers.news import _parse_date

log = logging.getLogger("terminal.cb")

# ── In-memory state ──────────────────────────────────────────────
live_states: dict = {}


def _fetch_communication_excerpt(url: str, max_chars: int = 12000) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=10)
        if resp.status_code != 200:
            return ""
        raw = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", resp.text, flags=re.I)
        raw = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", raw, flags=re.I)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        return raw[:max_chars]
    except Exception:
        return ""


def _attach_excerpt(bid: str, meta: Optional[dict]) -> None:
    if not meta or bid not in live_states:
        return
    link = (meta.get("link") or "").strip()
    if not link.startswith("http"):
        return
    ex = _fetch_communication_excerpt(link)
    if ex:
        live_states[bid]["communication_excerpt"] = ex


def _poll_single_bank_rss(bid: str, rss_urls: List[str]) -> Optional[dict]:
    """Lightweight RSS fallback for banks whose HTML scraper fails."""
    for url in rss_urls:
        try:
            resp = requests.get(url, headers=HTTP_HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            parsed = feedparser.parse(resp.content)
            entries = getattr(parsed, "entries", [])
            if entries:
                e = entries[0]
                dt = _parse_date(e)
                return {
                    "title": (e.get("title") or "").strip(),
                    "link": (e.get("link") or "").strip(),
                    "pubDate": dt.isoformat() if dt else "",
                }
        except Exception:
            continue
    return None


def _poll_bank_worker(bid, bank):
    """Poll a single bank, returns (bid, meta, latency_ms) or None."""
    t0 = time.time()
    meta = bank.fetch_latest_meta()
    latency = int((time.time() - t0) * 1000)
    return (bid, meta, latency)


def _build_state_dict(bid: str, meta: dict, latency: int) -> dict:
    bm = BANK_META.get(bid, {})
    return {
        "bank_id": bid,
        "bank_name": bm.get("name", bid.upper()),
        "short": bm.get("short", bid.upper()),
        "flag": bm.get("flag", ""),
        "ccy": bm.get("ccy", ""),
        "last_link": meta.get("link", ""),
        "last_pubdate": meta.get("pubDate", ""),
        "last_title": meta.get("title", ""),
        "last_run_ts": time.time(),
        "latency_ms": latency,
        "status": "ok",
    }


def poll_once():
    """Poll each bank via cb_sources and update live state."""
    global live_states
    try:
        sys.path.insert(0, str(CB_DIR))
        from cb_sources import BOE, FED, ECB, BOJ, BOC, RBA, RBNZ, SNB
        banks = {
            "fed": FED, "ecb": ECB, "boe": BOE, "boj": BOJ,
            "boc": BOC, "rba": RBA, "rbnz": RBNZ, "snb": SNB,
        }

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {}
            for bid, bank in banks.items():
                futures[pool.submit(_poll_bank_worker, bid, bank)] = bid

            for future in as_completed(futures, timeout=CB_BANK_TIMEOUT * 2):
                bid = futures[future]
                try:
                    result = future.result(timeout=CB_BANK_TIMEOUT)
                    if result:
                        _, meta, latency = result
                        if meta:
                            live_states[bid] = _build_state_dict(bid, meta, latency)
                            _attach_excerpt(bid, meta)
                            log.info(f"CB poll {bid}: {meta.get('title', '?')[:60]} ({latency}ms)")
                            continue
                except (TimeoutError, Exception) as e:
                    log.warning(f"CB poll {bid} failed: {e}")

                if bid in RSS_FALLBACKS:
                    log.info(f"CB poll {bid}: trying RSS fallback...")
                    t0 = time.time()
                    meta = _poll_single_bank_rss(bid, RSS_FALLBACKS[bid])
                    latency = int((time.time() - t0) * 1000)
                    if meta:
                        live_states[bid] = _build_state_dict(bid, meta, latency)
                        _attach_excerpt(bid, meta)
                        log.info(f"CB poll {bid} (RSS fallback): {meta.get('title', '?')[:60]} ({latency}ms)")
                    else:
                        log.warning(f"CB poll {bid}: RSS fallback also failed")

    except ImportError as e:
        log.warning(f"Cannot import cb_sources: {e} -- falling back to JSON states")
    except Exception as e:
        log.error(f"CB poll batch error: {e}")
    finally:
        if str(CB_DIR) in sys.path:
            sys.path.remove(str(CB_DIR))
    try:
        from storage.sqlite_store import persist_cb_states, persist_nlp_scores
        from analysis.cb_tone_live import enrich_cb_state
        from analysis.nlp_cb_desk import desk_payload_for_bank

        if live_states:
            persist_cb_states(dict(live_states))
            nlp = {
                bid: desk_payload_for_bank(bid, enrich_cb_state(bid, dict(st)))
                for bid, st in live_states.items()
            }
            persist_nlp_scores(nlp)
    except Exception as e:
        log.debug("cb sqlite persist: %s", e)


def poll_loop():
    """Background thread: poll banks every CB_POLL_SEC."""
    while True:
        try:
            poll_once()
        except Exception as e:
            log.error(f"CB poll loop error: {e}")
        time.sleep(CB_POLL_SEC)
