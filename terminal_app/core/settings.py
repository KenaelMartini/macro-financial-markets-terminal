from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, str(int(default))).strip().lower()
    return v in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    env: str
    project_root: Path
    terminal_data_dir: Path
    cb_dir: Path
    news_dir: Path
    sources_yaml: Path
    sqlite_path: Path
    sqlite_enabled: bool
    auth_enabled: bool
    api_key: str
    auth_user: str
    auth_password: str
    json_logs: bool
    fred_api_key: str
    finnhub_api_key: str
    ibkr_host: str
    ibkr_port: int
    ibkr_client_id: int


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    terminal_data = Path(os.environ.get("TERMINAL_DATA_DIR", str(project_root / "data"))).resolve()
    cb_override = os.environ.get("TERMINAL_CB_DIR", "").strip()
    news_override = os.environ.get("TERMINAL_NEWS_DIR", "").strip()

    cb_dir = Path(cb_override).resolve() if cb_override else (project_root / "data" / "vendors" / "cb")
    news_dir = Path(news_override).resolve() if news_override else (project_root / "data" / "vendors" / "news")
    terminal_data.mkdir(parents=True, exist_ok=True)

    return Settings(
        env=os.environ.get("TERMINAL_ENV", "dev").strip() or "dev",
        project_root=project_root,
        terminal_data_dir=terminal_data,
        cb_dir=cb_dir,
        news_dir=news_dir,
        sources_yaml=news_dir / "configs" / "sources.yaml",
        sqlite_path=Path(os.environ.get("TERMINAL_SQLITE_PATH", str(terminal_data / "terminal.db"))).resolve(),
        sqlite_enabled=_bool_env("TERMINAL_SQLITE", True),
        auth_enabled=_bool_env("TERMINAL_ENABLE_AUTH", False),
        api_key=os.environ.get("TERMINAL_API_KEY", "").strip(),
        auth_user=os.environ.get("TERMINAL_AUTH_USER", "terminal").strip() or "terminal",
        auth_password=os.environ.get("TERMINAL_AUTH_PASSWORD", "").strip(),
        json_logs=_bool_env("TERMINAL_JSON_LOG", False),
        fred_api_key=os.environ.get("FRED_API_KEY", "").strip(),
        finnhub_api_key=os.environ.get("FINNHUB_API_KEY", "").strip(),
        ibkr_host=os.environ.get("IBKR_HOST", "127.0.0.1").strip() or "127.0.0.1",
        ibkr_port=int(os.environ.get("IBKR_PORT", "7497")),
        ibkr_client_id=int(os.environ.get("IBKR_CLIENT_ID", "19")),
    )


SETTINGS = load_settings()

