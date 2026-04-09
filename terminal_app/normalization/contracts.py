from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    title: str
    url: str
    source: str
    published_utc: str
    summary: str = ""
    body_text: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: Optional[float] = None


class CentralBankEvent(BaseModel):
    bank_id: str
    title: str
    link: str = ""
    published_utc: str = ""
    source: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: Optional[float] = None


class MarketSnapshot(BaseModel):
    source: str = "ibkr"
    instruments: List[Dict[str, Any]] = Field(default_factory=list)
    last_refresh: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SignalOutput(BaseModel):
    signal_id: str
    category: str
    label: str
    score: float
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class RiskSnapshot(BaseModel):
    var_1d: Optional[float] = None
    cvar_1d: Optional[float] = None
    drawdown: Optional[float] = None
    confidence: Optional[float] = None
    source: str = "ibkr"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)

