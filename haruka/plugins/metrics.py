"""Command metrics plugin: quietly count how often each command is used.

Demonstrates the ``after_command`` hook — it augments userbot behaviour
(bookkeeping) without exposing a command of its own. Counts are stored in the
database under owner ``plugin.CommandMetrics`` and can be surfaced by other
tooling or the web panel.
"""
from __future__ import annotations

from haruka.core.plugins import Plugin


class CommandMetrics(Plugin):
    name = "CommandMetrics"
    description = "Counts command usage in the background."
    emoji = "\N{BAR CHART}"
    author = "haruka"
    version = "1.0.0"
    priority = 50
    options = {"enabled": True}

    async def after_command(self, ctx) -> None:
        if not self.option("enabled", True) or self.db is None:
            return
        command = getattr(ctx, "command", "") or "?"
        counts = dict(self.db.get("plugin.CommandMetrics", "counts", {}))
        counts[command] = int(counts.get(command, 0)) + 1
        await self.db.set("plugin.CommandMetrics", "counts", counts)
