# -*- coding: utf-8 -*-
"""
Corrélation simple entre série net_hawk NLP (SQLite) et rendements proxy SPY
d’après snapshots marché successifs.
"""

from __future__ import annotations

import json
import math
import sqlite3
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from config import ENABLE_SQLITE_PERSIST, SQLITE_PATH


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = min(len(xs), len(ys))
    if n < 5:
        return None
    xs = xs[:n]
    ys = ys[:n]
    mx = mean(xs)
    my = mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx <= 0 or deny <= 0:
        return None
    return round(num / (denx * deny), 4)


def _spy_from_payload(payload_json: str) -> Optional[float]:
    try:
        pj = json.loads(payload_json)
        for inst in pj.get("instruments") or []:
            if inst.get("symbol") == "SPY":
                return float(inst["price"])
    except Exception:
        return None
    return None


def _aligned_nh_spy_returns(bank_id: str, max_rows: int) -> Tuple[List[float], List[float]]:
    """Pour chaque ligne NLP (du plus récent au plus ancien), SPY du snapshot marché le plus récent avant captured_at."""
    nh_out: List[float] = []
    spy_ret_out: List[float] = []
    if not ENABLE_SQLITE_PERSIST:
        return nh_out, spy_ret_out
    try:
        c = sqlite3.connect(str(SQLITE_PATH), timeout=30.0)
        c.row_factory = sqlite3.Row
        mk_rows = c.execute(
            "SELECT captured_at, payload_json FROM market_snapshots ORDER BY id ASC"
        ).fetchall()
        spy_series: List[Tuple[str, float]] = []
        for r in mk_rows:
            px = _spy_from_payload(r["payload_json"])
            if px is not None:
                spy_series.append((r["captured_at"], px))
        if len(spy_series) < 4:
            c.close()
            return nh_out, spy_ret_out

        nlp_rows = c.execute(
            "SELECT captured_at, score_json FROM nlp_scores WHERE bank_id = ? ORDER BY id DESC LIMIT ?",
            (bank_id, max_rows),
        ).fetchall()
        c.close()

        pairs: List[Tuple[float, float]] = []
        for r in nlp_rows:
            try:
                sj = json.loads(r["score_json"])
                nh = sj.get("net_hawk")
                if nh is None:
                    continue
                ts = r["captured_at"]
                spy_px = None
                spy_prev = None
                for i in range(len(spy_series) - 1, -1, -1):
                    if spy_series[i][0] <= ts:
                        spy_px = spy_series[i][1]
                        if i > 0:
                            spy_prev = spy_series[i - 1][1]
                        break
                if spy_px is None or spy_prev is None or spy_prev == 0:
                    continue
                ret_bps = (spy_px - spy_prev) / spy_prev * 10000.0
                pairs.append((float(nh), ret_bps))
            except Exception:
                continue
        pairs.reverse()
        for a, b in pairs:
            nh_out.append(a)
            spy_ret_out.append(b)
    except Exception:
        return [], []
    return nh_out, spy_ret_out


def cb_tone_vs_spy_correlation(bank_id: str, lookback_rows: int = 40) -> Dict[str, Any]:
    nh, rets = _aligned_nh_spy_returns(bank_id, max(10, min(lookback_rows, 200)))
    corr = _pearson(nh, rets) if nh and rets else None
    return {
        "schema_version": 1,
        "bank_id": bank_id,
        "sample_size": min(len(nh), len(rets)),
        "correlation_net_hawk_vs_spy_return_bps": corr,
        "disclaimer": "Proxy : dernier snapshot SPY avant chaque score NLP, rendement vs observation précédente.",
    }
