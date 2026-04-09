"""Minimal fallback central bank sources for local boot.

This stub keeps the terminal operational without external legacy folders.
"""

from __future__ import annotations

from datetime import datetime, timezone


class _StubBank:
    def __init__(self, name: str):
        self.name = name

    def fetch_latest_meta(self) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "title": f"{self.name} feed unavailable (stub mode)",
            "link": "",
            "pubDate": now,
        }


FED = _StubBank("Federal Reserve")
ECB = _StubBank("European Central Bank")
BOE = _StubBank("Bank of England")
BOJ = _StubBank("Bank of Japan")
BOC = _StubBank("Bank of Canada")
RBA = _StubBank("Reserve Bank of Australia")
RBNZ = _StubBank("Reserve Bank of New Zealand")
SNB = _StubBank("Swiss National Bank")

