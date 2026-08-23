# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""
Runtime diagnostics for Haruka: uptime, resource usage, event-loop lag,
entity cache state and framework statistics in a single command.
"""

import asyncio
import gc
import logging
import platform
import time
import typing

import psutil
from telethon.tl.types import Message

from .. import loader, utils, version

logger = logging.getLogger(__name__)

_PROCESS = psutil.Process()


def _human_size(num: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(num) < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PiB"


def _human_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


class DiagnosticsMod(loader.Module):
    """Runtime health checks, resource usage and framework statistics"""

    strings = {"name": "Diagnostics"}

    def __init__(self):
        self._loop_lag_ms = 0.0
        self._lag_task: typing.Optional[asyncio.Task] = None

    async def _lag_watchdog(self):
        """Measures how late the event loop wakes up compared to schedule"""
        loop = asyncio.get_running_loop()
        expected = 5.0
        while True:
            started = loop.time()
            await asyncio.sleep(expected)
            self._loop_lag_ms = max(0.0, (loop.time() - started - expected) * 1000)

    async def client_ready(self):
        self._lag_task = asyncio.ensure_future(self._lag_watchdog())

    async def on_unload(self):
        if self._lag_task:
            self._lag_task.cancel()
            self._lag_task = None

    @loader.command()
    @loader.tag(alias="diag")
    async def health(self, message: Message):
        """Show runtime diagnostics: uptime, RAM, CPU, event loop lag, caches"""

        virtual_memory = psutil.virtual_memory()
        process_memory = _PROCESS.memory_info().rss
        cpu = psutil.cpu_percent(interval=None)
        uptime = time.time() - _PROCESS.create_time()

        try:
            import telethon as _telethon

            telethon_version = _telethon.__version__
        except Exception:
            telethon_version = "unknown"

        entity_cache = len(
            getattr(self.client, "_haruka_entity_cache", {}) or {}
        ) + len(getattr(self.client, "_haruka_perms_cache", {}) or {})

        gc_objects = len(gc.get_objects())

        modules_count = len(self.allmodules.modules)
        commands_count = len(self.allmodules.commands)
        watchers_count = len(self.allmodules.watchers)
        libraries_count = len(self.allmodules.libraries)

        lag = self._loop_lag_ms
        if lag < 50:
            lag_verdict = "🟢"
        elif lag < 250:
            lag_verdict = "🟡"
        else:
            lag_verdict = "🔴"

        ram_percent = process_memory / max(virtual_memory.total, 1) * 100

        text = (
            "<b>🩺 Haruka diagnostics</b>\n\n"
            "<b>⚙️ Runtime</b>\n"
            f"• Uptime: <code>{_human_uptime(uptime)}</code>\n"
            f"• Version: <code>{'.'.join(map(str, version.__version__))}</code>"
            f" (<code>{version.branch}</code>)\n"
            f"• Python: <code>{platform.python_version()}</code>"
            f" • Telethon: <code>{telethon_version}</code>\n"
            f"• OS: <code>{platform.system()} {platform.release()}</code>\n\n"
            "<b>📊 Resources</b>\n"
            f"• CPU: <code>{cpu:.1f}%</code>\n"
            f"• RAM (bot): <code>{_human_size(process_memory)}"
            f" ({ram_percent:.1f}% of total)</code>\n"
            f"• RAM (system): <code>{_human_size(virtual_memory.used)}"
            f" / {_human_size(virtual_memory.total)}</code>\n"
            f"{lag_verdict} Event loop lag: <code>{lag:.0f} ms</code>\n"
            f"• GC objects: <code>{gc_objects}</code>\n\n"
            "<b>🧩 Framework</b>\n"
            f"• Modules loaded: <code>{modules_count}</code>"
            f" • Libraries: <code>{libraries_count}</code>\n"
            f"• Commands: <code>{commands_count}</code>"
            f" • Watchers: <code>{watchers_count}</code>\n"
            f"• Entity cache records: <code>{entity_cache}</code>"
        )

        await utils.answer(message, text)

    @loader.command()
    async def gcstats(self, message: Message):
        """Run garbage collection now and show freed memory"""
        before = _PROCESS.memory_info().rss
        collected = gc.collect()
        after = _PROCESS.memory_info().rss
        freed = before - after
        await utils.answer(
            message,
            (
                "<b>♻️ GC complete</b>\n"
                f"• Objects collected: <code>{collected}</code>\n"
                f"• Memory freed: <code>{_human_size(max(freed, 0))}</code>\n"
                f"• Current RSS: <code>{_human_size(after)}</code>"
            ),
        )
