"""Visual skins shared by chat output and the engine Control Center."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    ok: str
    error: str
    warning: str
    loading: str
    info: str
    bullet: str
    arrow: str
    divider: str
    lock: str
    bot: str
    sparkle: str
    module: str
    clock: str
    fire: str
    bar_full: str = "▰"
    bar_empty: str = "▱"
    premium_ids: dict = field(default_factory=dict)


THEMES: dict[str, Theme] = {
    "aurora": Theme("aurora", "Aurora", "🟢", "🔴", "🟠", "◌", "🔵", "◦", "›", "━━━━━━━━━━━━━━━━", "🔐", "🤖", "✦", "◆", "◷", "✺"),
    "carbon": Theme("carbon", "Carbon", "◆", "◇", "▲", "◐", "●", "▪", "→", "────────────────", "▣", "▰", "✦", "⬡", "◴", "◆"),
    "minimal": Theme("minimal", "Minimal", "✓", "×", "!", "…", "i", "·", "→", "────────────────", "#", ">", "*", "+", "@", "!", "■", "□"),
}

_active: Theme = THEMES["aurora"]


def get_theme() -> Theme:
    return _active


def set_theme(name: str) -> Theme:
    global _active
    if name not in THEMES:
        raise KeyError(f"Unknown theme: {name}. Available: {', '.join(THEMES)}")
    _active = THEMES[name]
    return _active
