# -*- coding: utf-8 -*-
"""
Price-in analysis: narrative vs spot FX move (agreement + residual themes).
"""

import logging
from typing import Dict, Any, List

log = logging.getLogger("terminal.pricein")


def analyze_pricein(market_data: dict, signals: list) -> Dict[str, Any]:
    """
    Agreement score per pair: sign(actual_move) * sign(signal) * min(|move|,1).
    Residuals: themes where narrative and price disagree meaningfully.
    """
    instruments = market_data.get("instruments", [])
    if not instruments:
        return {
            "agreement": {},
            "residuals": [],
            "legend": (
                "Each row compares the keyword-based FX bias (from news) with today's "
                "percentage move in that pair from yfinance. "
                "Score near +1 = move aligns with bias; near -1 = opposite; ~0 = flat or unknown."
            ),
        }

    fx_moves: Dict[str, float] = {}
    fx_last: Dict[str, float] = {}
    for inst in instruments:
        if inst.get("asset_class") == "FX":
            name = inst.get("name") or ""
            fx_moves[name] = float(inst.get("change_pct") or 0)
            fx_last[name] = float(inst.get("price") or 0)

    if not signals:
        return {
            "agreement": {},
            "residuals": [
                {
                    "theme": "No active signal",
                    "pair": "—",
                    "description": "Need macro signals from news (refresh WIRE) and live FX prices.",
                    "impact": 0.0,
                }
            ],
            "legend": "Signals are empty — widen the news window or wait for the next refresh.",
        }

    agreement: Dict[str, float] = {}
    residuals: List[dict] = []

    for sig in signals:
        pair = sig["pair"]
        expected_dir = 1 if sig["direction"] == "LONG" else -1
        actual_move = fx_moves.get(pair)
        conv = float(sig.get("conviction") or 0)

        if actual_move is not None:
            if abs(actual_move) < 1e-6:
                agr = 0.0
            else:
                actual_dir = 1 if actual_move > 0 else -1
                agr = float(expected_dir * actual_dir * min(abs(actual_move), 1.0))
            agreement[pair] = round(agr, 4)
        else:
            agreement[pair] = 0.0

        # Residual: strong narrative vs weak / wrong price confirmation
        mismatch = conv >= 0.12 and abs(agreement.get(pair, 0)) < 0.35
        latest_px = fx_last.get(pair)
        score_arg = (
            f"Signal {sig['direction']} (conv {conv:.0%}) from {sig.get('driver') or 'macro lexicon'}; "
            f"dernier prix {latest_px:.5f} / move {actual_move:+.2f}%."
            if latest_px is not None and actual_move is not None
            else f"Signal {sig['direction']} (conv {conv:.0%}) from {sig.get('driver') or 'macro lexicon'}."
        )
        if mismatch:
            residuals.append({
                "theme": sig.get("driver") or "Macro tilt",
                "pair": pair,
                "description": (
                    f"{pair}: bias is {sig['direction']} (conv {conv:.0%}) but daily move "
                    f"({actual_move:+.2f}% if available) does not confirm — "
                    "possible positioning, liquidity, or unrelated drivers."
                ),
                "impact": round(conv * expected_dir, 3),
                "argument": score_arg,
            })

    # If still empty, show top conviction pairs as "watchlist" residuals
    if not residuals and signals:
        for sig in sorted(signals, key=lambda s: s.get("conviction", 0), reverse=True)[:4]:
            conv = float(sig.get("conviction") or 0)
            if conv < 0.08:
                continue
            pair = sig["pair"]
            am = fx_moves.get(pair)
            residuals.append({
                "theme": "Watchlist — " + (sig.get("driver") or "macro"),
                "pair": pair,
                "description": (
                    f"Bias {sig['direction']} (conv {conv:.0%}); spot move "
                    f"{(f'{am:+.2f}%' if am is not None else 'n/a')} — "
                    "monitor for catch-up or fade."
                ),
                "impact": round(conv, 3),
                "argument": score_arg,
            })

    return {
        "agreement": agreement,
        "residuals": residuals[:12],
        "latest_prices": {k: round(v, 6) for k, v in fx_last.items()},
        "legend": (
            "Agreement uses latest FX prices and today's % change vs the sign of the news-based signal. "
            "Residual rows highlight high-conviction stories that are not (yet) reflected in prices."
        ),
    }
