"""Inline companion bot.

A tiny bot account (token from @BotFather) that powers the Control Center and
inline forms. The userbot owner talks to it; everyone else is ignored. Kurigram
handles both accounts in the same process, so we just spin up a second Client.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from pyrogram import Client, filters
from pyrogram.handlers import CallbackQueryHandler, InlineQueryHandler
from pyrogram.types import (
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

if TYPE_CHECKING:
    from haruka.core.app import Application

logger = logging.getLogger(__name__)

CallbackHandler = Callable[[CallbackQuery], Awaitable[None]]


class InlineBot:
    """Owns the bot-side Client and routes callbacks to the Control Center."""

    def __init__(self, app: "Application", token: str):
        self.app = app
        self.token = token
        self._callbacks: dict[str, CallbackHandler] = {}
        self.username: Optional[str] = None

        self.bot = Client(
            name=f"{app.settings.session_name}_bot",
            api_id=app.client.app.api_id,
            api_hash=app.client.app.api_hash,
            bot_token=token,
            workdir=str(app.settings.data_dir),
        )

    # -- lifecycle -----------------------------------------------------

    async def start(self) -> None:
        from haruka.inline.units import InlineUnitManager

        self.units = InlineUnitManager(self.bot, self.app.security.owner_id)
        await self.units.start()
        self.bot.add_handler(CallbackQueryHandler(self._on_callback, self._owner_only()))
        self.bot.add_handler(InlineQueryHandler(self._on_inline, self._owner_only()))
        await self.bot.start()
        me = await self.bot.get_me()
        self.username = me.username

        # Control Center registers its own callback routes.
        from haruka.inline.control import ControlCenter

        self.control = ControlCenter(self.app, self)
        self.control.register()
        logger.info("Inline bot @%s ready", self.username)

    async def open_control_center(self) -> None:
        """Push the native engine shell to the owner's bot dialog."""
        await self.control.send_to_owner()

    async def bootstrap_owner(self, open_panel: bool = False) -> None:
        """Open the bot dialog for the owner and optionally push the home panel."""
        if self.username:
            try:
                await self.app.client.app.send_message(self.username, "/start")
            except Exception:
                logger.debug("Could not auto-open companion bot dialog", exc_info=True)
        if open_panel:
            try:
                await self.control.send_to_owner()
            except Exception:
                logger.debug("Could not push Control Center to owner", exc_info=True)

    async def stop(self) -> None:
        if hasattr(self, "units"):
            await self.units.stop()
        try:
            await self.bot.stop()
        except ConnectionError:
            pass

    # -- routing -------------------------------------------------------

    def on(self, prefix: str, handler: CallbackHandler) -> None:
        """Register a callback handler keyed by data prefix (e.g. ``cc:``)."""
        self._callbacks[prefix] = handler

    def _owner_only(self):
        owner_id = self.app.security.owner_id

        async def _check(_flt, _client, update) -> bool:
            return update.from_user is not None and update.from_user.id == owner_id

        return filters.create(_check)

    async def _on_callback(self, _client: Client, query: CallbackQuery) -> None:
        data = query.data or ""
        if data.startswith("unit:") and await self.units.dispatch(query):
            return
        for prefix, handler in self._callbacks.items():
            if data.startswith(prefix):
                try:
                    await handler(query)
                except Exception:
                    logger.exception("Callback handler failed for %s", data)
                    await query.answer("Something went wrong.", show_alert=True)
                return
        await query.answer()

    async def _on_inline(self, _client: Client, query: InlineQuery) -> None:
        # Minimal inline surface: type the bot username to open the Control Center.
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="Open Control Center",
                    description="Manage Haruka from here",
                    input_message_content=InputTextMessageContent("/start"),
                )
            ],
            cache_time=1,
        )
