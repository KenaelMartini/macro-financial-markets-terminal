# -*- coding: utf-8 -*-
"""
Live RSS news collector -- adapted from News Last 48H / news48_dump.py.
Runs as a background thread, refreshing every NEWS_REFRESH_SEC.
"""

import re
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests
import yaml
from dateutil import parser as dtparser

from config import (
    HTTP_HEADERS, SOURCES_YAML, DEFAULT_FEEDS,
    NEWS_WINDOW_HOURS, NEWS_MAX_WORKERS, NEWS_REFRESH_SEC,
)

log = logging.getLogger("terminal.news")


def _entry_body_text(entry: dict) -> str:
    """Best-effort full text from RSS/Atom (HTML stripped crudely)."""
    parts = []
    for c in entry.get("content") or []:
        if isinstance(c, dict):
            v = (c.get("value") or "").strip()
            if v:
                parts.append(v)
    if not parts:
        sm = (entry.get("summary") or "").strip()
        if sm:
            parts.append(sm)
    raw = " ".join(parts)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:16000]


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_utc: datetime
    summary: str = ""
    body_text: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_utc": self.published_utc.isoformat(),
            "summary": self.summary or self.title,
            "body_text": self.body_text or "",
        }


# ── In-memory state ──────────────────────────────────────────────
live_articles: List[dict] = []
feeds: List[str] = []
last_refresh: str = ""


def load_feeds() -> List[str]:
    if SOURCES_YAML.exists():
        try:
            data = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
            raw = data.get("feeds") or data.get("rss") or []
            clean = [f.lstrip("- ").strip() for f in raw if isinstance(f, str) and f.strip()]
            clean = [f for f in clean if f.startswith("http")]
            if clean:
                seen = set()
                deduped = [f for f in clean if f not in seen and not seen.add(f)]
                log.info(f"Loaded {len(deduped)} feeds from sources.yaml")
                return deduped
        except Exception as e:
            log.warning(f"Failed to load sources.yaml: {e}")
    log.info(f"Using {len(DEFAULT_FEEDS)} default feeds")
    return DEFAULT_FEEDS


def _parse_date(entry: dict) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed"):
        dt = entry.get(key)
        if dt:
            try:
                return datetime(*dt[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            d = dtparser.parse(raw)
            return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _collect_feed(url: str, cutoff: datetime) -> List[Article]:
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=12)
        if resp.status_code != 200:
            return []
        parsed = feedparser.parse(resp.content)
        feed_title = getattr(parsed, "feed", {}).get("title", url)
    except Exception:
        return []

    articles = []
    for e in getattr(parsed, "entries", []):
        dt = _parse_date(e)
        if not dt or dt < cutoff:
            continue
        title = re.sub(r"\s+", " ", (e.get("title") or "").strip())
        link = (e.get("link") or "").strip()
        if not title or not link:
            continue
        body = _entry_body_text(e)
        articles.append(Article(
            title=title,
            url=link,
            source=feed_title,
            published_utc=dt,
            summary=(e.get("summary") or title).strip()[:300],
            body_text=body,
        ))
    return articles


def collect_all(feed_list: List[str]) -> List[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_WINDOW_HOURS)
    all_articles: List[Article] = []

    with ThreadPoolExecutor(max_workers=NEWS_MAX_WORKERS) as pool:
        futures = {pool.submit(_collect_feed, url, cutoff): url for url in feed_list}
        for future in as_completed(futures):
            try:
                all_articles.extend(future.result())
            except Exception:
                pass

    seen_urls = set()
    deduped = []
    for a in sorted(all_articles, key=lambda x: x.published_utc, reverse=True):
        if a.url not in seen_urls:
            seen_urls.add(a.url)
            deduped.append(a)
    return deduped


def refresh_once():
    """Single collection cycle (used by worker supervisor)."""
    global live_articles, last_refresh
    t0 = time.time()
    articles = collect_all(feeds)
    live_articles = [a.to_dict() for a in articles]
    elapsed = time.time() - t0
    last_refresh = datetime.now(timezone.utc).isoformat()
    log.info(f"News refresh: {len(live_articles)} articles in {elapsed:.1f}s from {len(feeds)} feeds")
    try:
        from storage.sqlite_store import persist_after_news

        persist_after_news(live_articles)
    except Exception as e:
        log.debug("news persist skipped: %s", e)


def refresh_loop():
    """Background thread: collect news every NEWS_REFRESH_SEC."""
    while True:
        try:
            refresh_once()
        except Exception as e:
            log.error(f"News refresh error: {e}")
        time.sleep(NEWS_REFRESH_SEC)
