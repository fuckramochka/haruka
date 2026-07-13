"""Reply builders — the single way Haruka formats output.

All builders return HTML-parse-mode strings. Keep them dumb and consistent:
same statuses, same cards, same lists across every module.
"""

from __future__ import annotations

import html
from typing import Any, Iterable, Optional

from haruka.ui.theme import get_theme


def escape(text: Any) -> str:
    return html.escape(str(text), quote=False)


# -- status lines -------------------------------------------------------------


def ok(text: str) -> str:
    return f"{get_theme().ok} <b>{text}</b>"


def error(text: str) -> str:
    return f"{get_theme().error} <b>{text}</b>"


def warning(text: str) -> str:
    return f"{get_theme().warning} <b>{text}</b>"


def loading(text: str = "Processing...") -> str:
    return f"{get_theme().loading} <i>{text}</i>"


def info(text: str) -> str:
    return f"{get_theme().info} {text}"


# -- structured blocks ---------------------------------------------------------


def title(text: str, emoji: Optional[str] = None) -> str:
    glyph = emoji or get_theme().sparkle
    return f"{glyph} <b>{text}</b>"


def divider() -> str:
    return f"<i>{get_theme().divider}</i>"


def kv(rows: dict[str, Any]) -> str:
    """Aligned key-value block."""
    t = get_theme()
    return "\n".join(
        f"{t.bullet} <b>{escape(k)}:</b> {escape(v)}" for k, v in rows.items()
    )


def card(header: str, rows: dict[str, Any], emoji: Optional[str] = None) -> str:
    """A titled card: header, divider, key-value body."""
    return f"{title(header, emoji)}\n{divider()}\n{kv(rows)}"


def bullet_list(items: Iterable[Any], header: Optional[str] = None) -> str:
    t = get_theme()
    body = "\n".join(f"{t.bullet} {escape(i)}" for i in items)
    if header:
        return f"{title(header)}\n{divider()}\n{body}"
    return body


def numbered_list(items: Iterable[Any], header: Optional[str] = None) -> str:
    body = "\n".join(f"<b>{n}.</b> {escape(i)}" for n, i in enumerate(items, 1))
    if header:
        return f"{title(header)}\n{divider()}\n{body}"
    return body


def code_block(text: str, lang: str = "") -> str:
    return f"<pre language=\"{lang}\">{html.escape(text)}</pre>"


def mono(text: str) -> str:
    return f"<code>{html.escape(str(text))}</code>"


def progress(fraction: float, width: int = 12) -> str:
    """Text progress bar, 0.0..1.0."""
    t = get_theme()
    fraction = max(0.0, min(1.0, fraction))
    filled = round(fraction * width)
    return t.bar_full * filled + t.bar_empty * (width - filled) + f" {fraction:.0%}"


def command_help(prefix: str, name: str, usage: str, doc: str) -> str:
    usage_part = f" {escape(usage)}" if usage else ""
    doc_part = f" — {escape(doc)}" if doc else ""
    return f"<code>{escape(prefix + name)}</code>{usage_part}{doc_part}"
