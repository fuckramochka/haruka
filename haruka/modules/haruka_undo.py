# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""Undo: quickly delete your own recent messages in a chat"""

import collections
import logging

from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

MAX_TRACKED_PER_CHAT = 50


class UndoMod(loader.Module):
    """Delete your recent outgoing messages with one command"""

    strings = {"name": "Undo"}

    def __init__(self):
        self._recent = collections.defaultdict(
            lambda: collections.deque(maxlen=MAX_TRACKED_PER_CHAT)
        )

    @loader.command()
    async def undo(self, message: Message):
        """[count] — delete your last N (default 1) messages in this chat"""
        args = utils.get_args_raw(message)
        try:
            count = max(1, min(int(args or "1"), MAX_TRACKED_PER_CHAT))
        except ValueError:
            count = 1

        chat_id = utils.get_chat_id(message)

        # Never delete the `.undo` command message itself
        current_id = message.id
        targets = [
            msg_id
            for msg_id in reversed(self._recent.get(chat_id, ()))
            if msg_id != current_id
        ][:count]

        deleted = 0
        for msg_id in targets:
            try:
                await self.client.delete_messages(chat_id, msg_id)
                deleted += 1
            except Exception:
                logger.debug("Failed to delete message %s in %s", msg_id, chat_id)

        await utils.answer(message, f"🗑 <b>Deleted {deleted} message(s).</b>")

    @loader.watcher(out=True)
    async def watch_outgoing(self, message: Message):
        """Tracks outgoing message ids for later deletion"""
        chat_id = utils.get_chat_id(message)
        self._recent[chat_id].append(message.id)
