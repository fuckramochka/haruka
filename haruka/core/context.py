"""Command execution context.

Wraps the raw Kurigram message with everything a handler needs: parsed args,
services, and the UI render helpers — so module code stays tiny and every
reply goes through the design system.
"""

from __future__ import annotations

import logging
import shlex
from typing import TYPE_CHECKING, Any, Optional

from pyrogram.enums import ParseMode
from pyrogram.types import Message

from haruka.core.security import mask_secrets
from haruka.ui import render

if TYPE_CHECKING:
    from haruka.core.client import HarukaClient
    from haruka.core.database import Database
    from haruka.core.loader import Loader

logger = logging.getLogger(__name__)


class Context:
    """Everything a command handler needs, in one object."""

    def __init__(
        self,
        message: Message,
        client: "HarukaClient",
        db: "Database",
        loader: "Loader",
        command: str = "",
        args_raw: str = "",
    ):
        self.message = message
        self.client = client
        self.app = client.app
        self.db = db
        self.loader = loader
        self.command = command
        self.args_raw = args_raw

    # -- convenience accessors -------------------------------------------

    @property
    def core(self):
        """The :class:`Application` composition root (or ``None`` in tests)."""
        return getattr(self.loader, "app_ref", None)

    @property
    def security(self):
        """The shared :class:`SecurityManager`."""
        core = self.core
        return core.security if core is not None else None

    @property
    def translator(self):
        """The shared :class:`Translator`, if the app is wired."""
        core = self.core
        return getattr(core, "translator", None) if core is not None else None

    def t(self, key: str, default: Optional[str] = None, **values: Any) -> str:
        """Localize ``key`` in the active language (English fallback).

        Falls back to ``default`` (or the key itself) when no translator is
        available, so module and test code can call it unconditionally.
        """
        translator = self.translator
        if translator is None:
            text = default if default is not None else key
            try:
                return text.format(**values) if values else text
            except (KeyError, IndexError, ValueError):
                return text
        return translator.t(key, default, **values)

    @property
    def args(self) -> list[str]:
        """Shell-like arguments, preserving quoted values."""
        if not self.args_raw:
            return []
        try:
            return shlex.split(self.args_raw)
        except ValueError:
            return self.args_raw.split()

    @property
    def text(self) -> str:
        return self.message.text or self.message.caption or ""

    @property
    def topic_id(self) -> Optional[int]:
        """Forum topic id when the command was sent inside a topic."""
        return getattr(self.message, "message_thread_id", None)

    @property
    def chat_id(self) -> int:
        return self.message.chat.id

    @property
    def sender_id(self) -> Optional[int]:
        return self.message.from_user.id if self.message.from_user else None

    @property
    def sender_name(self) -> str:
        user = self.message.from_user
        return user.first_name if user else "?"

    @property
    def reply(self) -> Optional[Message]:
        return self.message.reply_to_message

    async def reply_text_or_none(self) -> Optional[str]:
        """Text of the replied-to message, if any."""
        if self.reply is None:
            return None
        return self.reply.text or self.reply.caption

    # -- responding (all output goes through the design system) -----------

    async def respond(self, text: str, **kwargs: Any) -> Message:
        """Edit own message (userbot style) or reply, masking secrets.

        Behaviour plugins get to transform every outgoing message here — this
        is the single choke point through which all userbot output flows.
        """
        text = mask_secrets(text)
        core = self.core
        manager = getattr(core, "plugins", None) if core is not None else None
        if manager is not None:
            try:
                text = await manager.apply_outgoing(text, self)
            except Exception:
                logger.debug("plugin outgoing transform failed", exc_info=True)
        kwargs.setdefault("parse_mode", ParseMode.HTML)
        try:
            if self.message.outgoing:
                return await self.message.edit_text(text, **kwargs)
            return await self.message.reply_text(text, **kwargs)
        except Exception:
            # Message may be too old to edit, deleted, etc. Fall back to reply.
            logger.debug("edit failed, falling back to reply", exc_info=True)
            return await self.message.reply_text(text, **kwargs)

    async def ok(self, text: str, **kwargs: Any) -> Message:
        return await self.respond(render.ok(text), **kwargs)

    async def error(self, text: str, **kwargs: Any) -> Message:
        return await self.respond(render.error(text), **kwargs)

    async def loading(self, text: str = "Processing...", **kwargs: Any) -> Message:
        return await self.respond(render.loading(text), **kwargs)

    async def card(self, title: str, rows: dict[str, Any], **kwargs: Any) -> Message:
        return await self.respond(render.card(title, rows), **kwargs)

    async def delete(self) -> None:
        try:
            await self.message.delete()
        except Exception:
            logger.debug("could not delete message", exc_info=True)
