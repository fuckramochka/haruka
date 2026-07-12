from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool(value: str | None, default: bool = False) -> bool:
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def _ids(value: str | None) -> frozenset[int]:
    if not value:
        return frozenset()
    return frozenset(int(item.strip()) for item in value.split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    name: str
    username: str
    data_dir: Path
    db_path: Path
    snapshot_dir: Path
    scan_interval_seconds: int
    style_refresh_interval_seconds: int
    snapshot_interval_seconds: int
    initiative_interval_seconds: int
    initiative_probability: float
    initiative_enabled: bool
    allowed_chat_ids: frozenset[int]
    max_scan_dialogs: int
    telegram_api_id: int
    telegram_api_hash: str
    telegram_bot_token: str | None
    telegram_session: Path
    telegram_bot_api_base: str
    ai_provider: str
    gemma_api_key: str
    gemma_api_base: str
    gemma_model: str
    ai_temperature: float
    ai_max_tokens: int
    dry_run: bool
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        data_dir = Path(os.getenv("HARUKA_DATA_DIR", "./data"))
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        if not api_id or not api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
        settings = cls(
            name=os.getenv("HARUKA_NAME", "Haruka"),
            username=os.getenv("HARUKA_USERNAME", "haruka").lstrip("@"),
            data_dir=data_dir,
            db_path=Path(os.getenv("HARUKA_DB_PATH", str(data_dir / "haruka.sqlite3"))),
            snapshot_dir=Path(os.getenv("HARUKA_SNAPSHOT_DIR", str(data_dir / "snapshots"))),
            scan_interval_seconds=int(os.getenv("HARUKA_SCAN_INTERVAL_SECONDS", "60")),
            style_refresh_interval_seconds=int(os.getenv("HARUKA_STYLE_REFRESH_INTERVAL_SECONDS", "21600")),
            snapshot_interval_seconds=int(os.getenv("HARUKA_SNAPSHOT_INTERVAL_SECONDS", "300")),
            initiative_interval_seconds=int(os.getenv("HARUKA_INITIATIVE_INTERVAL_SECONDS", "900")),
            initiative_probability=float(os.getenv("HARUKA_INITIATIVE_PROBABILITY", "0.03")),
            initiative_enabled=_bool(os.getenv("HARUKA_INITIATIVE_ENABLED"), False),
            allowed_chat_ids=_ids(os.getenv("HARUKA_ALLOWED_CHAT_IDS")),
            max_scan_dialogs=int(os.getenv("HARUKA_MAX_SCAN_DIALOGS", "50")),
            telegram_api_id=int(api_id),
            telegram_api_hash=api_hash,
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
            telegram_session=Path(os.getenv("TELEGRAM_SESSION", str(data_dir / "haruka.session"))),
            telegram_bot_api_base=os.getenv("TELEGRAM_BOT_API_BASE", "https://api.telegram.org"),
            ai_provider=os.getenv("AI_PROVIDER", "google_gemma"),
            gemma_api_key=os.getenv("GEMMA_API_KEY", ""),
            gemma_api_base=os.getenv("GEMMA_API_BASE", "").rstrip("/"),
            gemma_model=os.getenv("GEMMA_MODEL", "google/gemma-3-27b-it"),
            ai_temperature=float(os.getenv("AI_TEMPERATURE", "0.82")),
            ai_max_tokens=int(os.getenv("AI_MAX_TOKENS", "500")),
            dry_run=_bool(os.getenv("HARUKA_DRY_RUN"), False),
            log_level=os.getenv("HARUKA_LOG_LEVEL", "INFO"),
        )
        if not 0 <= settings.initiative_probability <= 1:
            raise ValueError("HARUKA_INITIATIVE_PROBABILITY must be between 0 and 1")
        if min(settings.scan_interval_seconds, settings.snapshot_interval_seconds) < 5:
            raise ValueError("Runtime intervals must be at least 5 seconds")
        return settings
