"""Built-in engine preferences used by every management surface."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from haruka.core.database import Database


@dataclass(frozen=True)
class EnginePreferences:
    style: str = "aurora"
    compact_help: bool = False
    reveal_errors: bool = False
    confirm_dangerous: bool = True
    quiet_unknown: bool = True


class PreferenceStore:
    STYLES = ("aurora", "carbon", "minimal")

    def __init__(self, db: "Database"):
        self.db = db

    def get(self) -> EnginePreferences:
        raw = self.db.get("core", "preferences", {}) or {}
        allowed = EnginePreferences.__dataclass_fields__
        clean = {key: value for key, value in raw.items() if key in allowed}
        if clean.get("style") not in self.STYLES:
            clean.pop("style", None)
        return EnginePreferences(**clean)

    async def set(self, key: str, value) -> EnginePreferences:
        if key not in EnginePreferences.__dataclass_fields__:
            raise KeyError(key)
        current = asdict(self.get())
        if key == "style" and value not in self.STYLES:
            raise ValueError(f"Unknown style: {value}")
        current[key] = value
        await self.db.set("core", "preferences", current)
        return EnginePreferences(**current)

    async def toggle(self, key: str) -> EnginePreferences:
        current = self.get()
        value = getattr(current, key)
        if not isinstance(value, bool):
            raise TypeError(f"{key} is not boolean")
        return await self.set(key, not value)

    async def cycle_style(self) -> EnginePreferences:
        current = self.get()
        index = (self.STYLES.index(current.style) + 1) % len(self.STYLES)
        return await self.set("style", self.STYLES[index])
