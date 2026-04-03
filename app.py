# -*- coding: utf-8 -*-
"""
KMCO Bloomberg-style Terminal v4 -- multi-screen FastAPI application.
Entry point: python app.py
"""

from __future__ import annotations

import base64
from typing import List
import json
import logging
import os
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from alerts.store import load as load_alerts
from config import (
    CALENDAR_REFRESH_SEC,
    CB_POLL_SEC,
    ENABLE_AUTH,
    NEWS_REFRESH_SEC,
    STATIC_DIR,
    TERMINAL_API_KEY,
    TERMINAL_AUTH_PASSWORD,
    TERMINAL_AUTH_USER,
    get_paths_health,
)
from routes import router
from scrapers import calendar, cb_poller, ibkr, news
from storage.sqlite_store import init_db
from workers.supervisor import start_supervised_workers


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_USE_JSON_LOG = os.environ.get("TERMINAL_JSON_LOG", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
_handlers: List[logging.Handler] = [logging.StreamHandler(sys.stdout)]
if _USE_JSON_LOG:
    _jh = logging.StreamHandler(sys.stdout)
    _jh.setFormatter(_JsonLogFormatter())
    _handlers = [_jh]
else:
    _sh = logging.StreamHandler(sys.stdout)
    _sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _handlers = [_sh]

logging.basicConfig(level=logging.INFO, handlers=_handlers, force=True)
log = logging.getLogger("terminal")


class _NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """En dev, évite que le navigateur garde d’anciens JS/CSS."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        p = request.url.path
        if p.startswith("/static") or p == "/":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response


class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not ENABLE_AUTH:
            return await call_next(request)
        path = request.url.path
        if path in ("/health", "/", "/favicon.ico") or path.startswith("/static"):
            return await call_next(request)
        ok = False
        if TERMINAL_API_KEY and request.headers.get("X-API-Key") == TERMINAL_API_KEY:
            ok = True
        if not ok and TERMINAL_AUTH_PASSWORD:
            auth = request.headers.get("Authorization") or ""
            if auth.startswith("Basic "):
                try:
                    raw = base64.b64decode(auth[6:].strip()).decode("utf-8", errors="replace")
                    u, _, p = raw.partition(":")
                    if u == TERMINAL_AUTH_USER and p == TERMINAL_AUTH_PASSWORD:
                        ok = True
                except Exception:
                    pass
        if not ok:
            return JSONResponse(
                {"detail": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="terminal"'},
            )
        return await call_next(request)


app = FastAPI(title="KMCO Terminal", docs_url=None, redoc_url=None)
app.add_middleware(_NoCacheStaticMiddleware)
if ENABLE_AUTH:
    app.add_middleware(_AuthMiddleware)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)


@app.get("/health")
async def health():
    from storage.sqlite_store import db_stats
    from workers.supervisor import workers_status_snapshot

    paths = get_paths_health()
    dbs = db_stats()
    workers = workers_status_snapshot()
    ok_paths = paths.get("cb_dir_exists") and paths.get("news_dir_exists") and paths.get("sources_yaml_exists")
    ok_db = (not dbs.get("enabled")) or (dbs.get("exists") and "error" not in dbs)
    healthy = ok_paths and ok_db
    return {
        "status": "healthy" if healthy else "degraded",
        "paths_ok": ok_paths,
        "sqlite_ok": ok_db,
        "workers": workers,
        "paths": paths,
        "sqlite": dbs,
    }


@app.on_event("startup")
def on_startup():
    init_db()
    news.feeds = news.load_feeds()
    load_alerts()
    ph = get_paths_health()
    log.info("Paths health: %s", ph)
    if not ph.get("sources_yaml_exists"):
        log.warning("sources.yaml introuvable — flux RSS par défaut du package.")
    if not ph.get("cb_dir_exists"):
        log.warning("CB_DIR absent — poll banques centrales limité (import cb_sources).")
    log.info("Starting supervised background workers...")
    start_supervised_workers(
        [
            ("news", news.refresh_once, float(NEWS_REFRESH_SEC)),
            ("cb_poller", cb_poller.poll_once, float(CB_POLL_SEC)),
            ("calendar", calendar.refresh_once, float(CALENDAR_REFRESH_SEC)),
            ("ibkr", ibkr.refresh_once, 35.0),
        ]
    )


if __name__ == "__main__":
    import uvicorn

    print("\n  [*]  KMCO Terminal v4 (LIVE) starting on http://127.0.0.1:8800\n")
    print("  [*]  Tip: use --reload while coding so Python changes apply without restart.\n")
    uvicorn.run(app, host="127.0.0.1", port=8800, log_level="info")
