# -*- coding: utf-8 -*-
"""
Static data loaders: read JSON/JSONL files from Central Bank Monitoring.
"""

import json
from pathlib import Path

from config import CB_DIR, BANK_ORDER, BANK_META


def read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_jsonl_tail(path: Path, n: int = 5) -> list:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
        return out
    except Exception:
        return []


def read_jsonl_tail_filtered(path: Path, n: int = 50, scan_last_lines: int = 400) -> list:
    """
    Lit les dernières lignes d’un JSONL, parse, filtre démo/saleté (via analysis.cb_tone_live).
    """
    from analysis.cb_tone_live import filter_stored_cb_event

    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        chunk = lines[-scan_last_lines:] if len(lines) > scan_last_lines else lines
        good = []
        for line in chunk:
            try:
                ev = json.loads(line)
                if filter_stored_cb_event(ev):
                    good.append(ev)
            except Exception:
                pass
        return good[-n:] if len(good) > n else good
    except Exception:
        return []


def load_cb_states() -> dict:
    states = {}
    states_dir = CB_DIR / "data" / "states"
    if not states_dir.exists():
        return states
    for bank_id in BANK_ORDER:
        f = states_dir / f"{bank_id}.json"
        data = read_json(f)
        if data:
            meta = BANK_META.get(bank_id, {})
            data.update(
                bank_id=bank_id,
                bank_name=meta.get("name", bank_id.upper()),
                short=meta.get("short", bank_id.upper()),
                flag=meta.get("flag", ""),
                ccy=meta.get("ccy", ""),
            )
            states[bank_id] = data
    return states


def load_calendar_file() -> list:
    """Fallback: read stale calendar JSON if live fetch hasn't run yet."""
    return read_json(CB_DIR / "ff_calendar_thisweek.json") or []


def load_cb_events(n_per_bank: int = 20) -> dict:
    """Événements CB filtrés (sans entrées de démo évidentes dans JSONL)."""
    events = {}
    history_dir = CB_DIR / "data" / "history"
    if not history_dir.exists():
        return events
    for bank_dir in history_dir.iterdir():
        if bank_dir.is_dir():
            bank_events = read_jsonl_tail_filtered(
                bank_dir / "events.jsonl", n=n_per_bank, scan_last_lines=500
            )
            if bank_events:
                events[bank_dir.name.lower().replace(" ", "_")] = bank_events
    return events
