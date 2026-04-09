from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from storage.sqlite_store import (
    fetch_history_calendar,
    fetch_history_cb_snapshots,
    fetch_history_news,
    fetch_nlp_history,
    persist_after_calendar,
    persist_after_news,
    persist_cb_states,
    persist_market_snapshot,
    persist_nlp_scores,
)


@dataclass
class HistoryRepository:
    def news(self, since_iso: str, limit: int = 500) -> List[dict]:
        return fetch_history_news(since_iso, limit)

    def calendar(self, since_iso: str, limit: int = 300) -> List[dict]:
        return fetch_history_calendar(since_iso, limit)

    def cb_snapshots(self, bank_id: str, limit: int = 50) -> List[dict]:
        return fetch_history_cb_snapshots(bank_id, limit)

    def nlp(self, bank_id: str, limit: int = 60) -> List[dict]:
        return fetch_nlp_history(bank_id, limit)


@dataclass
class PersistRepository:
    def news(self, articles: List[dict]) -> None:
        persist_after_news(articles)

    def calendar(self, rows: List[dict]) -> None:
        persist_after_calendar(rows)

    def cb_states(self, rows: Dict[str, dict]) -> None:
        persist_cb_states(rows)

    def market(self, snapshot: Dict[str, Any]) -> None:
        persist_market_snapshot(snapshot)

    def nlp_scores(self, scores: Dict[str, dict]) -> None:
        persist_nlp_scores(scores)

