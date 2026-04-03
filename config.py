# -*- coding: utf-8 -*-
"""
Global configuration: paths, constants, bank metadata.
"""

import os
import socket
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parent

# Données locales du terminal (toujours sous le package)
TERMINAL_DATA_DIR = Path(
    os.environ.get("TERMINAL_DATA_DIR", str(BASE / "data"))
).resolve()
TERMINAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Dépendances externes : surcharger par ENV si les dossiers « sœurs » bougent
_cb_override = os.environ.get("TERMINAL_CB_DIR", "").strip()
_news_override = os.environ.get("TERMINAL_NEWS_DIR", "").strip()
CB_DIR = Path(_cb_override).resolve() if _cb_override else (PROJECT_ROOT / "Central Bank Monitoring")
NEWS_DIR = Path(_news_override).resolve() if _news_override else (PROJECT_ROOT / "News Last 48H")
SOURCES_YAML = NEWS_DIR / "configs" / "sources.yaml"
TEMPLATES_DIR = BASE / "templates"
STATIC_DIR = BASE / "static"

SQLITE_PATH = Path(
    os.environ.get("TERMINAL_SQLITE_PATH", str(TERMINAL_DATA_DIR / "terminal.db"))
).resolve()
ENABLE_SQLITE_PERSIST = os.environ.get("TERMINAL_SQLITE", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Auth / ops (phase 6)
ENABLE_AUTH = os.environ.get("TERMINAL_ENABLE_AUTH", "0").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
TERMINAL_API_KEY = os.environ.get("TERMINAL_API_KEY", "").strip()
TERMINAL_AUTH_USER = os.environ.get("TERMINAL_AUTH_USER", "terminal").strip()
TERMINAL_AUTH_PASSWORD = os.environ.get("TERMINAL_AUTH_PASSWORD", "").strip()

# Courbes de taux (phase 3) — clé FRED optionnelle
FRED_API_KEY = os.environ.get("FRED_API_KEY", "").strip()


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
    }

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
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "").strip()

# ── IBKR / TWS API ───────────────────────────────────────────────
IBKR_HOST = os.environ.get("IBKR_HOST", "127.0.0.1").strip() or "127.0.0.1"
IBKR_PORT = int(os.environ.get("IBKR_PORT", "7497"))
IBKR_CLIENT_ID = int(os.environ.get("IBKR_CLIENT_ID", "19"))
