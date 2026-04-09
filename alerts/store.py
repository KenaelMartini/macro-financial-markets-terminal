# -*- coding: utf-8 -*-
"""
Alert persistence: store alert configs in a JSON file.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

log = logging.getLogger("terminal.alerts")

ALERTS_FILE = Path(__file__).resolve().parent.parent / "data" / "alerts.json"

_alerts: List[Dict] = []


def _ensure_dir():
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load() -> List[Dict]:
    global _alerts
    if ALERTS_FILE.exists():
        try:
            _alerts = json.loads(ALERTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            _alerts = []
    return _alerts


def save():
    _ensure_dir()
    ALERTS_FILE.write_text(json.dumps(_alerts, indent=2), encoding="utf-8")


def add_alert(alert_type: str, bank: str = "", value: str = "") -> List[Dict]:
    global _alerts
    _alerts.append({
        "type": alert_type,
        "bank": bank,
        "value": value,
        "created": datetime.now(timezone.utc).isoformat(),
        "triggered": False,
        "message": f"{alert_type}: {value}" + (f" ({bank.upper()})" if bank else ""),
    })
    save()
    return _alerts


def get_alerts() -> List[Dict]:
    return _alerts


def trigger_alert(index: int, message: str):
    if 0 <= index < len(_alerts):
        _alerts[index]["triggered"] = True
        _alerts[index]["message"] = message
        save()
