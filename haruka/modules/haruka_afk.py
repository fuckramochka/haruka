# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""AFK mode: automatic replies while you are away"""

import contextlib
import logging
import time

from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


class AfkMod(loader.Module):
    """Toggle AFK mode with automatic replies to incoming messages"""

    strings = {"name": "AFK"}

    def __init__(self):
        self._afk_since = None
        self._reason = ""
        self._notified = {}

    async def client_ready(self):
        if self.get("active", False):
            self._afk_since = self.get("since", time.time())
            self._reason = self.get("reason", "")

    def _save_state(self):
        self.set("active", self._afk_since is not None)
        self.set("since", self._afk_since)
        self.set("reason", self._reason)

    @staticmethod
    def _format_duration(seconds) -> str:
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        parts = []
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds and not hours:
            parts.append(f"{seconds}s")
        return " ".join(parts) or "0s"

    @loader.command()
    async def afk(self, message: Message):
        """<reason> — toggle AFK mode with optional reason"""
        if self._afk_since is not None:
            duration = self._format_duration(time.time() - self._afk_since)
            self._afk_since = None
            self._reason = ""
            self._save_state()
            await utils.answer(
                message, f"🟢 <b>AFK disabled.</b> You were away {duration}"
            )
            return

        args = utils.get_args_raw(message)
        self._afk_since = time.time()
        self._reason = args or ""
        self._save_state()
        text = "🌙 <b>AFK enabled.</b>"
        if self._reason:
            text += f" Reason: <i>{utils.escape_html(self._reason)}</i>"
        await utils.answer(message, text)

    def _should_notify(self, sender_id) -> bool:
        if len(self._notified) > 500:
            self._notified.clear()

        last = self._notified.get(sender_id, 0)
        if time.time() - last > 300:
            self._notified[sender_id] = time.time()
            return True
        return False

    @loader.watcher()
    async def watch_afk(self, message: Message):
        """Auto-replies while AFK"""
        if self._afk_since is None or message.out:
            return

        is_pm = getattr(message, "is_private", False)
        mentioned = False

        if not is_pm:
            with contextlib.suppress(Exception):
                me = await self.client.get_me()
                text = message.raw_text or ""
                mentioned = bool(me.username) and f"@{me.username}" in text

        if not is_pm and not mentioned:
            return

        sender_id = getattr(message, "sender_id", None)
        if sender_id is None or not self._should_notify(sender_id):
            return

        away = self._format_duration(time.time() - self._afk_since)
        text = f"🌙 <b>I'm AFK right now</b> (away for <code>{away}</code>)"
        if self._reason:
            text += f"\n💬 <b>Reason:</b> <i>{utils.escape_html(self._reason)}</i>"

        with contextlib.suppress(Exception):
            await message.respond(text)
