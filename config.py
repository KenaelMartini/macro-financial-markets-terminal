# -*- coding: utf-8 -*-
"""
Global configuration: paths, constants, bank metadata.
Single source of truth is app.core.settings.SETTINGS.
"""

import socket
from pathlib import Path

from terminal_app.core.settings import SETTINGS

# ── Paths ─────────────────────────────────────────────────────────
BASE = SETTINGS.project_root
PROJECT_ROOT = SETTINGS.project_root
TERMINAL_DATA_DIR = SETTINGS.terminal_data_dir
CB_DIR = SETTINGS.cb_dir
NEWS_DIR = SETTINGS.news_dir
SOURCES_YAML = SETTINGS.sources_yaml
TEMPLATES_DIR = BASE / "templates"
STATIC_DIR = BASE / "static"
SQLITE_PATH = SETTINGS.sqlite_path
ENABLE_SQLITE_PERSIST = SETTINGS.sqlite_enabled

# Auth / ops
ENABLE_AUTH = SETTINGS.auth_enabled
TERMINAL_API_KEY = SETTINGS.api_key
TERMINAL_AUTH_USER = SETTINGS.auth_user
TERMINAL_AUTH_PASSWORD = SETTINGS.auth_password
FRED_API_KEY = SETTINGS.fred_api_key

# ── Networking ────────────────────────────────────────────────────
socket.setdefaulttimeout(12)

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Chrome/130.0",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── News Scraper ──────────────────────────────────────────────────
NEWS_WINDOW_HOURS = 168  # 7 days — wider wire than 48h
NEWS_MAX_WORKERS = 16
NEWS_REFRESH_SEC = 300

DEFAULT_FEEDS = [
    "https://news.google.com/rss/search?q=site:reuters.com+markets",
    "https://news.google.com/rss/search?q=site:reuters.com+central+bank",
    "https://news.google.com/rss/search?q=site:reuters.com+economy",
    "https://news.google.com/rss/search?q=site:bloomberg.com+markets",
    "https://news.google.com/rss/search?q=site:bloomberg.com+economics",
    "https://news.google.com/rss/search?q=site:ft.com+markets",
    "https://news.google.com/rss/search?q=site:ft.com+central+banks",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.ecb.europa.eu/rss/press.xml",
    "https://www.imf.org/external/np/exr/feeds/rss.aspx?feed=PressReleases",
]

# ── Central Bank Poller ───────────────────────────────────────────
CB_POLL_SEC = 90
CB_BANK_TIMEOUT = 25

BANK_META = {
    "fed":  {"name": "Federal Reserve",            "short": "FED",  "flag": "\U0001f1fa\U0001f1f8", "ccy": "USD"},
    "ecb":  {"name": "European Central Bank",      "short": "ECB",  "flag": "\U0001f1ea\U0001f1fa", "ccy": "EUR"},
    "boe":  {"name": "Bank of England",            "short": "BOE",  "flag": "\U0001f1ec\U0001f1e7", "ccy": "GBP"},
    "boj":  {"name": "Bank of Japan",              "short": "BOJ",  "flag": "\U0001f1ef\U0001f1f5", "ccy": "JPY"},
    "boc":  {"name": "Bank of Canada",             "short": "BOC",  "flag": "\U0001f1e8\U0001f1e6", "ccy": "CAD"},
    "rba":  {"name": "Reserve Bank of Australia",   "short": "RBA",  "flag": "\U0001f1e6\U0001f1fa", "ccy": "AUD"},
    "rbnz": {"name": "Reserve Bank of New Zealand", "short": "RBNZ", "flag": "\U0001f1f3\U0001f1ff", "ccy": "NZD"},
    "snb":  {"name": "Swiss National Bank",         "short": "SNB",  "flag": "\U0001f1e8\U0001f1ed", "ccy": "CHF"},
}
BANK_ORDER = ["fed", "ecb", "boe", "boj", "boc", "rba", "rbnz", "snb"]

RSS_FALLBACKS = {
    "rba": [
        "https://www.rba.gov.au/rss/rss.xml",
        "https://news.google.com/rss/search?q=site:rba.gov.au",
        "https://news.google.com/rss/search?q=%22Reserve+Bank+of+Australia%22",
    ],
    "rbnz": [
        "https://www.rbnz.govt.nz/rss.xml",
        "https://news.google.com/rss/search?q=site:rbnz.govt.nz",
    ],
}

# ── Calendar ──────────────────────────────────────────────────────
FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CALENDAR_REFRESH_SEC = 600
# Optional: economic calendar with actuals (free tier: https://finnhub.io/register )
FINNHUB_API_KEY = SETTINGS.finnhub_api_key

# ── IBKR / TWS API ───────────────────────────────────────────────
IBKR_HOST = SETTINGS.ibkr_host
IBKR_PORT = SETTINGS.ibkr_port
IBKR_CLIENT_ID = SETTINGS.ibkr_client_id


def get_paths_health() -> dict:
    """État des chemins critiques (pour /api/status et /health)."""
    return {
        "cb_dir": str(CB_DIR),
        "cb_dir_exists": CB_DIR.is_dir(),
        "news_dir": str(NEWS_DIR),
        "news_dir_exists": NEWS_DIR.is_dir(),
        "sources_yaml": str(SOURCES_YAML),
        "sources_yaml_exists": SOURCES_YAML.is_file(),
        "terminal_data_dir": str(TERMINAL_DATA_DIR),
        "sqlite_path": str(SQLITE_PATH),
        "sqlite_persist_enabled": ENABLE_SQLITE_PERSIST,
        "env": SETTINGS.env,
    }
