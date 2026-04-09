from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def ok(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "meta": meta or {},
    }


def error(code: str, detail: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = ok(data=None, meta=meta)
    out["status"] = "error"
    out["error"] = {"code": code, "detail": detail}
    return out

