# -*- coding: utf-8 -*-
"""
SQLite persistence (WAL) for news, calendar, CB snapshots, market snapshots, NLP scores.
"""

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import SQLITE_PATH, ENABLE_SQLITE_PERSIST

log = logging.getLogger("terminal.storage")

_lock = threading.Lock()
_initialized = False


def _conn() -> sqlite3.Connection:
    Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(SQLITE_PATH), check_same_thread=False, timeout=30.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def init_db() -> None:
    global _initialized
    if not ENABLE_SQLITE_PERSIST:
        return
    with _lock:
        if _initialized:
            return
        try:
            c = _conn()
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    source TEXT,
                    published_utc TEXT,
                    summary TEXT,
                    body_text TEXT,
                    ingested_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_articles_pub ON articles(published_utc);

                CREATE TABLE IF NOT EXISTS calendar_events (
                    id TEXT PRIMARY KEY,
                    date TEXT,
                    country TEXT,
                    title TEXT,
                    impact TEXT,
                    forecast TEXT,
                    previous TEXT,
                    actual TEXT,
                    raw_json TEXT,
                    ingested_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cal_date ON calendar_events(date);

                CREATE TABLE IF NOT EXISTS cb_states_snapshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cb_bank ON cb_states_snapshot(bank_id, captured_at);

                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_json TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS nlp_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_id TEXT NOT NULL,
                    score_json TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_nlp_bank ON nlp_scores(bank_id, captured_at);
                """
            )
            _ensure_article_body_column(c)
            c.commit()
            c.close()
            _initialized = True
            log.info("SQLite initialized at %s", SQLITE_PATH)
        except Exception as e:
            log.error("SQLite init failed: %s", e)


def _ensure_article_body_column(c: sqlite3.Connection) -> None:
    cols = {row[1] for row in c.execute("PRAGMA table_info(articles)").fetchall()}
    if "body_text" not in cols:
        try:
            c.execute("ALTER TABLE articles ADD COLUMN body_text TEXT")
        except Exception as e:
            log.warning("Could not add body_text column: %s", e)


def persist_after_news(articles: List[dict]) -> None:
    if not ENABLE_SQLITE_PERSIST or not articles:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _lock:
            c = _conn()
            _ensure_article_body_column(c)
            for a in articles:
                c.execute(
                    """INSERT OR REPLACE INTO articles (url,title,source,published_utc,summary,body_text,ingested_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        (a.get("url") or "")[:2000],
                        (a.get("title") or "")[:2000],
                        (a.get("source") or "")[:500],
                        (a.get("published_utc") or "")[:40],
                        (a.get("summary") or "")[:2000],
                        (a.get("body_text") or "")[:16000],
                        now,
                    ),
                )
            c.commit()
            c.close()
    except Exception as e:
        log.debug("persist news: %s", e)


def persist_after_calendar(events: List[dict]) -> None:
    if not ENABLE_SQLITE_PERSIST or not events:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _lock:
            c = _conn()
            for ev in events:
                uid = f"{ev.get('date','')}|{ev.get('country','')}|{ev.get('title','')}"[:500]
                c.execute(
                    """INSERT OR REPLACE INTO calendar_events
                       (id,date,country,title,impact,forecast,previous,actual,raw_json,ingested_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        uid,
                        str(ev.get("date") or "")[:40],
                        str(ev.get("country") or "")[:12],
                        str(ev.get("title") or "")[:500],
                        str(ev.get("impact") or "")[:20],
                        str(ev.get("forecast") or "")[:80],
                        str(ev.get("previous") or "")[:80],
                        str(ev.get("actual") or "")[:80],
                        json.dumps(ev, ensure_ascii=False)[:8000],
                        now,
                    ),
                )
            c.commit()
            c.close()
    except Exception as e:
        log.debug("persist calendar: %s", e)


def persist_cb_states(states: Dict[str, dict]) -> None:
    if not ENABLE_SQLITE_PERSIST or not states:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _lock:
            c = _conn()
            for bid, st in states.items():
                c.execute(
                    "INSERT INTO cb_states_snapshot (bank_id, payload_json, captured_at) VALUES (?,?,?)",
                    (bid, json.dumps(st, ensure_ascii=False, default=str)[:12000], now),
                )
            c.commit()
            c.close()
    except Exception as e:
        log.debug("persist cb: %s", e)


def persist_market_snapshot(mkt: dict) -> None:
    if not ENABLE_SQLITE_PERSIST or not mkt:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _lock:
            c = _conn()
            c.execute(
                "INSERT INTO market_snapshots (payload_json, captured_at) VALUES (?,?)",
                (json.dumps(mkt, ensure_ascii=False, default=str)[:500000], now),
            )
            c.commit()
            c.close()
    except Exception as e:
        log.debug("persist market: %s", e)


def persist_nlp_scores(scores: Dict[str, dict]) -> None:
    if not ENABLE_SQLITE_PERSIST or not scores:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _lock:
            c = _conn()
            for bid, payload in scores.items():
                c.execute(
                    "INSERT INTO nlp_scores (bank_id, score_json, captured_at) VALUES (?,?,?)",
                    (bid, json.dumps(payload, ensure_ascii=False, default=str)[:8000], now),
                )
            c.commit()
            c.close()
    except Exception as e:
        log.debug("persist nlp: %s", e)


def db_stats() -> Dict[str, Any]:
    if not ENABLE_SQLITE_PERSIST:
        return {"enabled": False}
    p = Path(SQLITE_PATH)
    out: Dict[str, Any] = {
        "enabled": True,
        "path": str(SQLITE_PATH),
        "exists": p.is_file(),
        "bytes": p.stat().st_size if p.is_file() else 0,
    }
    if not p.is_file():
        return out
    try:
        c = _conn()
        for table in ("articles", "calendar_events", "cb_states_snapshot", "market_snapshots", "nlp_scores"):
            row = c.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
            out[f"count_{table}"] = row["n"] if row else 0
        c.close()
    except Exception as e:
        out["error"] = str(e)
    return out


def fetch_history_news(since_iso: str, limit: int = 500) -> List[dict]:
    if not ENABLE_SQLITE_PERSIST:
        return []
    try:
        c = _conn()
        rows = c.execute(
            "SELECT url,title,source,published_utc,summary,body_text,ingested_at FROM articles "
            "WHERE published_utc >= ? ORDER BY published_utc DESC LIMIT ?",
            (since_iso, limit),
        ).fetchall()
        c.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def fetch_history_calendar(since_iso: str, limit: int = 300) -> List[dict]:
    if not ENABLE_SQLITE_PERSIST:
        return []
    try:
        c = _conn()
        rows = c.execute(
            "SELECT * FROM calendar_events WHERE date >= ? ORDER BY date DESC LIMIT ?",
            (since_iso, limit),
        ).fetchall()
        c.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def fetch_history_cb_snapshots(bank_id: str, limit: int = 50) -> List[dict]:
    if not ENABLE_SQLITE_PERSIST:
        return []
    try:
        c = _conn()
        rows = c.execute(
            "SELECT bank_id, payload_json, captured_at FROM cb_states_snapshot "
            "WHERE bank_id = ? ORDER BY id DESC LIMIT ?",
            (bank_id, limit),
        ).fetchall()
        c.close()
        out = []
        for r in rows:
            try:
                out.append(
                    {
                        "bank_id": r["bank_id"],
                        "captured_at": r["captured_at"],
                        "state": json.loads(r["payload_json"]),
                    }
                )
            except Exception:
                continue
        return out
    except Exception:
        return []


def fetch_nlp_history(bank_id: str, limit: int = 60) -> List[dict]:
    if not ENABLE_SQLITE_PERSIST:
        return []
    try:
        c = _conn()
        rows = c.execute(
            "SELECT bank_id, score_json, captured_at FROM nlp_scores "
            "WHERE bank_id = ? ORDER BY id DESC LIMIT ?",
            (bank_id, limit),
        ).fetchall()
        c.close()
        out = []
        for r in rows:
            try:
                out.append(
                    {
                        "bank_id": r["bank_id"],
                        "captured_at": r["captured_at"],
                        "scores": json.loads(r["score_json"]),
                    }
                )
            except Exception:
                continue
        return out
    except Exception:
        return []
