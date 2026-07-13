"""Command router.

A single Kurigram message handler feeds this dispatcher, which:

1. resolves the active prefix and aliases,
2. matches a command,
3. enforces role + rate limits via :class:`SecurityManager`,
4. builds a :class:`Context` and runs the handler (with error rendering),
5. fans messages out to passive watchers.

There is exactly one place where commands are parsed and one place where
errors are handled — no scattered try/excepts in modules.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import TYPE_CHECKING, Optional

from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from haruka.core.context import Context
from haruka.core.security import Role, mask_secrets
from haruka.ui import render

if TYPE_CHECKING:
    from haruka.core.client import HarukaClient
    from haruka.core.database import Database
    from haruka.core.loader import Loader
    from haruka.core.security import SecurityManager

logger = logging.getLogger(__name__)

PROTECTED_TELEGRAM_IDS = {777000, 489000}


class Dispatcher:
    def __init__(
        self,
        client: "HarukaClient",
        db: "Database",
        loader: "Loader",
        security: "SecurityManager",
    ):
        self.client = client
        self.db = db
        self.loader = loader
        self.security = security
        self._handler = None
        self._watcher_tasks: set[asyncio.Task] = set()
        self._watcher_slots = asyncio.Semaphore(100)

    # -- setup -----------------------------------------------------------

    def install(self) -> None:
        """Register the master message handler on the client."""
        # Own outgoing messages (userbot commands) + incoming (for watchers
        # and for lower-privilege commands issued by sudo users).
        self._handler = MessageHandler(self._on_message, filters.all & ~filters.service)
        self.client.app.add_handler(self._handler)

    async def stop(self) -> None:
        """Detach handlers and cancel remaining watcher tasks."""
        if self._handler is not None:
            self.client.app.remove_handler(self._handler)
            self._handler = None
        tasks = list(self._watcher_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # -- config helpers --------------------------------------------------

    @property
    def prefix(self) -> str:
        return self.db.get("core", "prefix", ".")

    def _aliases(self) -> dict[str, str]:
        return self.db.get("core", "aliases", {})

    def _blacklisted_chats(self) -> set[int]:
        return {int(c) for c in self.db.get("core", "blacklist_chats", [])}

    def _blacklisted_users(self) -> set[int]:
        return {int(u) for u in self.db.get("core", "blacklist_users", [])}

    def _is_blacklisted(self, chat_id: Optional[int], sender_id: Optional[int]) -> bool:
        """Heroku-style blacklist: ignore commands from muted chats/users.

        The owner is never blacklisted so recovery is always possible.
        """
        if sender_id is not None and sender_id == self.security.owner_id:
            return False
        if chat_id is not None and chat_id in self._blacklisted_chats():
            return True
        if sender_id is not None and sender_id in self._blacklisted_users():
            return True
        return False

    # -- entrypoint ------------------------------------------------------

    async def _on_message(self, _, message: Message) -> None:
        try:
            text = message.text or message.caption or ""
            if text and text.startswith(self.prefix):
                handled = await self._route_command(message, text)
                if handled:
                    return
            await self._run_watchers(message)
        except Exception:  # noqa: BLE001 - top-level safety net
            logger.exception("Unhandled error in dispatcher")

    # -- command routing -------------------------------------------------

    async def _route_command(self, message: Message, text: str) -> bool:
        body = text[len(self.prefix):]
        if not body.strip():
            return False

        head, _, tail = body.partition(" ")
        head = head.lower()

        # Alias expansion.
        aliases = self._aliases()
        if head in aliases:
            expanded = aliases[head]
            e_head, _, e_tail = expanded.partition(" ")
            head = e_head.lower()
            tail = (e_tail + " " + tail).strip()

        bound = self.loader.find_command(head)
        if bound is None:
            # Unknown prefixed text is ordinary Telegram text, not an error.
            # Never edit/reply to it and let passive watchers decide whether
            # they care about the message.
            return False

        sender_id = message.from_user.id if message.from_user else None
        if message.outgoing and sender_id is None:
            sender_id = self.security.owner_id
        if sender_id in PROTECTED_TELEGRAM_IDS:
            return True
        if self._is_blacklisted(getattr(message.chat, "id", None), sender_id):
            return True
        if not self.loader.is_module_enabled(bound.module.name) or not self.loader.is_command_enabled(bound.name):
            return True

        # Only the owner may drive from their own outgoing messages; other
        # roles must satisfy the command's required role from incoming ones.
        if not self.security.check(sender_id, bound.spec.role):
            if message.outgoing:  # silently ignore own too-low calls? no — inform
                await message.reply_text(render.error("Insufficient permissions."))
            return True

        if sender_id and not self.security.rate_limiter.allow(sender_id, head):
            await message.reply_text(render.warning("Rate limit — slow down."))
            return True

        ctx = Context(
            message=message,
            client=self.client,
            db=self.db,
            loader=self.loader,
            command=head,
            args_raw=tail.strip(),
        )

        await self.db.audit(
            "command",
            f"{head} {tail}".strip(),
            actor=sender_id,
            chat_id=getattr(message.chat, "id", None),
        )
        await self._execute(bound.handler, ctx, head)
        return True

    async def _execute(self, handler, ctx: Context, head: str) -> None:
        try:
            await handler(ctx)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - rendered to user
            tb = mask_secrets(traceback.format_exc())
            logger.error("Command '%s' failed: %s", head, exc)
            core = getattr(self.loader, "app_ref", None)
            preferences = getattr(core, "preferences", None)
            reveal = bool(preferences and preferences.get().reveal_errors)
            details = render.code_block(tb[-1200:], "python") if reveal else ""
            try:
                message = render.error(
                    render.escape(f"{type(exc).__name__}: {exc}")
                )
                if details:
                    message += f"\n{details}"
                else:
                    message += "\n" + render.info("Enable error details in Control Center for a traceback.")
                await ctx.respond(message)
            except Exception:
                logger.debug("could not report error to chat", exc_info=True)

    # -- watchers --------------------------------------------------------

    async def _run_watchers(self, message: Message) -> None:
        watchers = self.loader.watchers
        sender = message.from_user
        if not watchers or (sender and sender.id in PROTECTED_TELEGRAM_IDS):
            return
        if self._is_blacklisted(getattr(message.chat, "id", None), sender.id if sender else None):
            return
        is_group = message.chat and message.chat.type.name in {"GROUP", "SUPERGROUP"}
        is_private = message.chat and message.chat.type.name == "PRIVATE"

        text = message.text or message.caption or ""
        for bound in watchers:
            if not self.loader.is_module_enabled(bound.module.name):
                continue
            spec = bound.spec
            if message.outgoing and not spec.outgoing:
                continue
            if not message.outgoing and not spec.incoming:
                continue
            if spec.only_groups and not is_group:
                continue
            if spec.only_private and not is_private:
                continue
            if spec.only_reply and message.reply_to_message is None:
                continue
            if spec.only_forward and getattr(message, "forward_origin", None) is None:
                continue
            if spec.only_mention and not getattr(message, "mentioned", False):
                continue
            if spec.no_bots and sender and getattr(sender, "is_bot", False):
                continue
            if spec.no_commands and text.startswith(self.prefix):
                continue
            ctx = Context(message, self.client, self.db, self.loader)
            task = asyncio.create_task(self._safe_watcher(bound.handler, ctx))
            self._watcher_tasks.add(task)
            task.add_done_callback(self._watcher_tasks.discard)

    async def _safe_watcher(self, handler, ctx: Context) -> None:
        async with self._watcher_slots:
            try:
                await handler(ctx)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Watcher error in %s", getattr(handler, "__name__", "?"))
