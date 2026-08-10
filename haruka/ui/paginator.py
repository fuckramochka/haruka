"""Pagination for long replies.

Splits long content into Telegram-sized chunks. Used by help, logs, terminal
output — anything that can exceed the 4096-char message limit.
"""

from __future__ import annotations

TELEGRAM_LIMIT = 4096
SAFE_LIMIT = 3900  # leave headroom for headers / html tags


def split_pages(text: str, limit: int = SAFE_LIMIT) -> list[str]:
    """Split text into pages on line boundaries where possible."""
    if len(text) <= limit:
        return [text]

    pages: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.split("\n"):
        # A single line longer than the limit gets hard-split.
        while len(line) > limit:
            if current:
                pages.append("\n".join(current))
                current, current_len = [], 0
            pages.append(line[:limit])
            line = line[limit:]

        if current_len + len(line) + 1 > limit:
            pages.append("\n".join(current))
            current, current_len = [], 0

        current.append(line)
        current_len += len(line) + 1

    if current:
        pages.append("\n".join(current))
    return pages


def page_footer(page: int, total: int) -> str:
    return f"\n\n<i>page {page}/{total}</i>" if total > 1 else ""
