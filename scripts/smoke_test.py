from __future__ import annotations

import json
import urllib.request


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    base = "http://127.0.0.1:8800"
    endpoints = ["/health", "/api/status", "/api/system/status"]
    for ep in endpoints:
        payload = get(base + ep)
        print(ep, "=>", ("status" in payload) or ("server_time" in payload))


if __name__ == "__main__":
    main()
