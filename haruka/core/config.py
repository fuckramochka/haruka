"""Runtime configuration.

Environment-driven settings (validated with pydantic) plus a light typed
config system that modules use to declare their own options.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


def _base_dir() -> Path:
    override = os.environ.get("HARUKA_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".haruka"


class Settings(BaseModel):
    """Process-level settings sourced from environment variables."""

    api_id: Optional[int] = Field(default=None)
    api_hash: Optional[str] = Field(default=None)
    telegram_proxy: Optional[str] = None
    data_dir: Path = Field(default_factory=_base_dir)
    session_name: str = "haruka"
    # AI (any OpenAI-compatible endpoint: OpenAI, OpenRouter, Groq, Ollama...)
    ai_api_key: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_model: str = "gpt-4o-mini"
    web_enabled: bool = True
    web_host: str = "127.0.0.1"
    web_port: int = 8080
    web_open_browser: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        def _int(name: str) -> Optional[int]:
            raw = os.environ.get(name)
            return int(raw) if raw and raw.isdigit() else None

        return cls(
            api_id=_int("API_ID"),
            api_hash=os.environ.get("API_HASH") or None,
            telegram_proxy=os.environ.get("TELEGRAM_PROXY") or None,
            session_name=os.environ.get("HARUKA_SESSION", "haruka"),
            ai_api_key=os.environ.get("AI_API_KEY") or None,
            ai_base_url=os.environ.get("AI_BASE_URL") or None,
            ai_model=os.environ.get("AI_MODEL", "gpt-4o-mini"),
            web_enabled=os.environ.get("HARUKA_WEB", "1").lower() in {"1", "true", "yes"},
            web_host=os.environ.get("HARUKA_WEB_HOST", "127.0.0.1"),
            web_port=int(os.environ.get("HARUKA_WEB_PORT", "8080")),
            web_open_browser=os.environ.get("HARUKA_WEB_OPEN", "1").lower()
            in {"1", "true", "yes"},
        )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "haruka.db"

    @property
    def modules_dir(self) -> Path:
        return self.data_dir / "modules"


@dataclass
class ConfigOption:
    """A single declared config option of a module."""

    name: str
    default: Any
    doc: str = ""
    validator: Optional[Callable[[Any], Any]] = None

    def validate(self, value: Any) -> Any:
        if self.validator is not None:
            return self.validator(value)
        return value


class ModuleConfig:
    """Declarative, db-backed config for a module.

    Modules declare options once; values are persisted in the database and
    editable from the Control Center::

        self.config = ModuleConfig(
            ConfigOption("interval", 60, "Polling interval in seconds", int),
        )
    """

    def __init__(self, *options: ConfigOption):
        self._options: dict[str, ConfigOption] = {o.name: o for o in options}
        self._values: dict[str, Any] = {}
        self._persist: Optional[Callable[[str, Any], Any]] = None

    def bind(self, stored: dict[str, Any], persist: Callable[[str, Any], Any]) -> None:
        """Attach persisted values and a persistence callback (set by loader)."""
        self._persist = persist
        for name, value in stored.items():
            if name in self._options:
                self._values[name] = value

    @property
    def options(self) -> dict[str, ConfigOption]:
        return dict(self._options)

    def __contains__(self, name: str) -> bool:
        return name in self._options

    def __getitem__(self, name: str) -> Any:
        if name in self._values:
            return self._values[name]
        return self._options[name].default

    async def set(self, name: str, value: Any) -> None:
        option = self._options[name]
        value = option.validate(value)
        self._values[name] = value
        if self._persist is not None:
            result = self._persist(name, value)
            if hasattr(result, "__await__"):
                await result

    def as_dict(self) -> dict[str, Any]:
        return {name: self[name] for name in self._options}


@dataclass
class Alias:
    """Command alias mapping."""

    alias: str
    command: str
    args_prefix: str = ""


@dataclass
class CoreConfig:
    """User-tunable core settings persisted in the db under owner 'core'."""

    prefix: str = "."
    aliases: dict[str, str] = field(default_factory=dict)
    language: str = "en"
