# -*- coding: utf-8 -*-
"""
Superviseur de workers : une itération = un tick ; compteurs last_ok / erreurs / redémarrages.
"""

from __future__ import annotations

import logging
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

log = logging.getLogger("terminal.supervisor")


@dataclass
class WorkerInfo:
    name: str
    last_ok_ts: float = 0.0
    last_error: str = ""
    last_tick_ts: float = 0.0
    tick_count: int = 0
    error_count: int = 0
    consecutive_errors: int = 0
    restart_count: int = 0


WORKER_REGISTRY: Dict[str, WorkerInfo] = {}


def _info(name: str) -> WorkerInfo:
    if name not in WORKER_REGISTRY:
        WORKER_REGISTRY[name] = WorkerInfo(name=name)
    return WORKER_REGISTRY[name]


def tick_worker(name: str, fn: Callable[[], None], sleep_sec: float) -> None:
    """Boucle : appelle fn() puis sleep. Backoff si erreurs consécutives."""

    info = _info(name)
    backoff = 5.0
    max_backoff = 120.0
    while True:
        info.last_tick_ts = time.time()
        try:
            fn()
            info.last_ok_ts = time.time()
            info.last_error = ""
            info.tick_count += 1
            info.consecutive_errors = 0
            backoff = 5.0
        except Exception as e:
            info.error_count += 1
            info.consecutive_errors += 1
            info.last_error = f"{type(e).__name__}: {e}"
            log.error("[%s] worker tick failed: %s", name, info.last_error)
            log.debug(traceback.format_exc())
            if info.consecutive_errors >= 3:
                sleep_extra = min(backoff, max_backoff)
                info.restart_count += 1
                log.warning("[%s] backing off %.0fs after %d errors (restart_count=%d)", name, sleep_extra, info.consecutive_errors, info.restart_count)
                time.sleep(sleep_extra)
                backoff = min(backoff * 1.5, max_backoff)
        time.sleep(sleep_sec)


def workers_status_snapshot() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, info in WORKER_REGISTRY.items():
        out[name] = {
            "last_ok_ts": info.last_ok_ts,
            "last_error": info.last_error,
            "last_tick_ts": info.last_tick_ts,
            "tick_count": info.tick_count,
            "error_count": info.error_count,
            "consecutive_errors": info.consecutive_errors,
            "restart_count": info.restart_count,
        }
    return out


def start_supervised_workers(jobs: List[tuple]) -> None:
    """
    jobs: list of (name, callable, sleep_seconds)
    Démarre un thread daemon par job.
    """
    for name, fn, sec in jobs:
        t = threading.Thread(target=tick_worker, args=(name, fn, float(sec)), daemon=True, name=f"worker-{name}")
        t.start()
        log.info("Started supervised worker: %s (every %.0fs)", name, sec)
