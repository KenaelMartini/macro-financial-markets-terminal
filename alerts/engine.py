# -*- coding: utf-8 -*-
"""
Alert evaluation engine: checks conditions against live data.
"""

import logging
from typing import List, Dict

log = logging.getLogger("terminal.alerts.engine")


def evaluate_alerts(alerts: List[Dict], cb_states: dict, articles: list,
                    calendar: list, market_data: dict) -> List[Dict]:
    """Check all alerts against current data and mark triggered ones."""
    triggered = []
    for i, alert in enumerate(alerts):
        if alert.get("triggered"):
            continue
        atype = alert.get("type", "")

        if atype == "cb_new":
            bank = alert.get("bank", "")
            if bank and bank in cb_states:
                st = cb_states[bank]
                if st.get("last_title") and alert.get("value"):
                    if alert["value"].lower() in st["last_title"].lower():
                        alert["triggered"] = True
                        alert["message"] = f"CB Alert: {st['last_title']}"
                        triggered.append(alert)

        elif atype == "news_keyword":
            kw = (alert.get("value") or "").lower()
            if kw:
                for art in articles[:50]:
                    if kw in (art.get("title", "") + art.get("summary", "")).lower():
                        alert["triggered"] = True
                        alert["message"] = f"Keyword '{kw}' found: {art.get('title', '')[:60]}"
                        triggered.append(alert)
                        break

    return triggered
