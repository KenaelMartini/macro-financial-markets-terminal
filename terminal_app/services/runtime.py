from __future__ import annotations

from alerts.store import load as load_alerts
from config import CALENDAR_REFRESH_SEC, CB_POLL_SEC, NEWS_REFRESH_SEC, get_paths_health
from scrapers import calendar, cb_poller, ibkr, news
from storage.sqlite_store import init_db
from workers.supervisor import start_supervised_workers


def bootstrap_runtime(logger) -> None:
    init_db()
    news.feeds = news.load_feeds()
    load_alerts()
    ph = get_paths_health()
    logger.info("Paths health: %s", ph)
    if not ph.get("sources_yaml_exists"):
        logger.warning("sources.yaml introuvable — fallback feeds activé.")
    if not ph.get("cb_dir_exists"):
        logger.warning("CB_DIR absent — poll banques centrales en mode fallback.")
    start_supervised_workers(
        [
            ("news", news.refresh_once, float(NEWS_REFRESH_SEC)),
            ("cb_poller", cb_poller.poll_once, float(CB_POLL_SEC)),
            ("calendar", calendar.refresh_once, float(CALENDAR_REFRESH_SEC)),
            ("ibkr", ibkr.refresh_once, 35.0),
        ]
    )

