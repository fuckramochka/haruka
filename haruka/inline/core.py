"""Inline buttons, galleries and other Telegram-Bot-API stuff"""

# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import contextlib
import logging
import time
import typing

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError, TelegramUnauthorizedError
from telethon.errors.rpcerrorlist import InputUserDeactivatedError, YouBlockedUserError
from telethon.tl.functions.contacts import UnblockRequest
from telethon.tl.functions.messages import (
    GetDialogFiltersRequest,
    UpdateDialogFilterRequest,
)
from telethon.tl.types import DialogFilter, InputPeerUser, Message
from telethon.utils import get_display_name

from .. import utils
from ..database import Database
from ..tl_cache import CustomTelegramClient
from ..translations import Translator
from .bot_pm import BotPM
from .events import Events
from .form import Form
from .gallery import Gallery
from .list import List
from .query_gallery import QueryGallery
from .token_obtainment import TokenObtainment
from .utils import Utils

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from ..loader import Modules


class InlineManager(
    Utils,
    Events,
    TokenObtainment,
    Form,
    Gallery,
    QueryGallery,
    List,
    BotPM,
):
    """
    Inline buttons, galleries and other Telegram-Bot-API stuff
    :param client: Telegram client
    :param db: Database instance
    :param allmodules: All modules
    :type client: haruka.tl_cache.CustomTelegramClient
    :type db: haruka.database.Database
    :type allmodules: haruka.loader.Modules
    """

    def __init__(
        self,
        client: CustomTelegramClient,
        db: Database,
        allmodules: "Modules",  # type: ignore  # noqa: F821
    ):
        """Initialize InlineManager to create forms"""
        self._client = client
        self._db = db
        self._allmodules = allmodules
        self.translator: Translator = allmodules.translator

        self._units: typing.Dict[str, dict] = {}
        self._custom_map: typing.Dict[str, callable] = {}
        self.fsm: typing.Dict[str, str] = {}
        self._web_auth_tokens: typing.List[str] = []
        self._error_events: typing.Dict[str, asyncio.Event] = {}

        self._markup_ttl = 60 * 60 * 24
        self.init_complete = False

        self._token = db.get("haruka.inline", "bot_token", False)

        self._me: int = None
        self._name: str = None
        self._dp: Dispatcher = None
        self._task: asyncio.Future = None
        self._cleaner_task: asyncio.Future = None
        self.bot: Bot = None
        self.bot_id: int = None
        self.bot_username: str = None

    async def _cleaner(self):
        """Cleans outdated inline units"""
        while True:
            for unit_id, unit in self._units.copy().items():
                if (unit.get("ttl") or (time.time() + self._markup_ttl)) < time.time():
                    del self._units[unit_id]

            await asyncio.sleep(5)

    @staticmethod
    async def _build_bot(token: str):
        """
        Create the aiogram Bot, falling back to certificate-verification-free
        HTTPS when a local MITM proxy (self-signed cert) breaks the default
        verified connection to api.telegram.org.
        """
        import ssl

        from aiogram.client.session.aiohttp import AiohttpSession
        from aiohttp import ClientConnectorCertificateError

        bot = Bot(
            token=token,
            session=AiohttpSession(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        try:
            await bot.get_me()
            return bot
        except TelegramUnauthorizedError:
            raise
        except ClientConnectorCertificateError as e:
            if "self-signed" not in str(e) and "CERTIFICATE_VERIFY_FAILED" not in str(
                e
            ):
                raise

        logger.warning(
            "TLS interception detected (self-signed certificate)."
            " Using unverified HTTPS for the inline bot API calls"
        )
        insecure_ctx = ssl.create_default_context()
        insecure_ctx.check_hostname = False
        insecure_ctx.verify_mode = ssl.CERT_NONE

        session = AiohttpSession()
        # AiohttpSession builds its connector from this dict on first request
        session._connector_init["ssl"] = insecure_ctx

        return Bot(
            token=token,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    async def register_manager(
        self,
        after_break: bool = False,
        ignore_token_checks: bool = False,
    ):
        """
        Register manager
        :param after_break: Loop marker
        :param ignore_token_checks: If `True`, will not check for token
        :type after_break: bool
        :type ignore_token_checks: bool
        :return: None
        :rtype: None
        """
        self._me = self._client.tg_id
        self._name = get_display_name(self._client.haruka_me)

        if not ignore_token_checks:
            is_token_asserted = await self.assert_token()
            if not is_token_asserted:
                self.init_complete = False
                return

        self.init_complete = True

        self.bot = await self._build_bot(self._token)
        self._bot = self.bot
        self._dp = Dispatcher()

        try:
            bot_me = await self.bot.get_me()
            self.bot_username = bot_me.username
            self.bot_id = bot_me.id
        except TelegramUnauthorizedError:
            logger.critical("Token expired, revoking...")
            return await self.dp_revoke_token(False)

        try:
            m = await self._client.send_message(self.bot_username, "/start haruka init")
        except InputUserDeactivatedError:
            # Bot genuinely deleted - forget its token and start over once
            self._db.set("haruka.inline", "bot_token", None)
            self._token = False

            if not after_break:
                return await self.register_manager(True)

            self.init_complete = False
            return False
        except YouBlockedUserError:
            await self._client(UnblockRequest(id=self.bot_username))
            try:
                m = await self._client.send_message(
                    self.bot_username, "/start haruka init"
                )
            except Exception:
                logger.critical("Can't unblock users bot", exc_info=True)
                return False
        except ValueError:
            # Entity resolution can fail transiently right after bot creation.
            # The stored token is fine - DO NOT wipe it, just retry later.
            logger.warning(
                "Could not resolve inline bot entity yet - keeping token,"
                " inline features will activate after next restart"
            )
            self.init_complete = False
            return False
        except Exception:
            self.init_complete = False
            logger.critical("Initialization of inline manager failed!", exc_info=True)
            return False

        _folders = await self._client(GetDialogFiltersRequest())
        for folder in _folders.filters:
            if getattr(folder, "title", None) == "Haruka":
                if any(
                    [
                        isinstance(peer, InputPeerUser) and peer.user_id == self.bot_id
                        for peer in folder.include_peer
                    ]
                ):
                    break

                pinned = [await self._client.get_input_entity(self.bot_id)]
                include = folder.include_peers
                exclude = folder.exclude_peers
                emoticon = folder.emoticon
                color = folder.color

                await self._client(
                    UpdateDialogFilterRequest(
                        folder.id,
                        DialogFilter(
                            folder.id,
                            pinned_peers=pinned,
                            include_peers=include,
                            exclude_peers=exclude,
                            emoticon=emoticon,
                            color=color,
                        ),
                    )
                )
                break

        await self._client.delete_messages(self.bot_username, m)

        self._dp.inline_query.register(
            self._inline_handler,
            lambda _: True,
        )

        self._dp.callback_query.register(
            self._callback_query_handler,
            lambda _: True,
        )

        self._dp.chosen_inline_result.register(
            self._chosen_inline_handler,
            lambda _: True,
        )

        self._dp.message.register(
            self._message_handler,
            lambda *_: True,
        )

        old = self.bot.get_updates
        conflicts = 0

        async def new(*args, **kwargs):
            nonlocal conflicts
            try:
                result = await old(*args, **kwargs)
                conflicts = 0
                return result
            except TelegramConflictError:
                # 409 Conflict: someone else is polling the same bot - most
                # likely a leftover duplicate Haruka instance. Revoking the
                # token here would create a brand-new bot on every restart,
                # so instead just warn and back off.
                conflicts += 1
                logger.warning(
                    "TelegramConflictError while polling inline bot (%s)."
                    " Another instance is probably running - close duplicate"
                    " Haruka processes! (consecutive: %s)",
                    self.bot_username,
                    conflicts,
                )
                await asyncio.sleep(3)
                return []

        self.bot.get_updates = new

        self._task = asyncio.ensure_future(
            self._dp.start_polling(self._bot, handle_signals=False)
        )
        self._cleaner_task = asyncio.ensure_future(self._cleaner())

    async def _stop(self):
        """Stop the bot"""
        self._task.cancel()
        await self._dp.stop_polling()
        self._cleaner_task.cancel()

    def pop_web_auth_token(self, token: str) -> bool:
        """
        Check if web confirmation button was pressed
        :param token: Token to check
        :type token: str
        :return: `True` if token was found, `False` otherwise
        :rtype: bool
        """
        if token not in self._web_auth_tokens:
            return False

        self._web_auth_tokens.remove(token)
        return True

    async def _invoke_unit(self, unit_id: str, message: Message) -> Message:
        event = asyncio.Event()
        self._error_events[unit_id] = event

        q: "InlineResults" = None  # type: ignore  # noqa: F821
        exception: Exception = None

        async def result_getter():
            nonlocal unit_id, q
            with contextlib.suppress(Exception):
                q = await self._client.inline_query(self.bot_username, unit_id)

        async def event_poller():
            nonlocal exception
            await asyncio.wait_for(event.wait(), timeout=10)
            if self._error_events.get(unit_id):
                exception = self._error_events[unit_id]

        result_getter_task = asyncio.ensure_future(result_getter())
        event_poller_task = asyncio.ensure_future(event_poller())

        _, pending = await asyncio.wait(
            [result_getter_task, event_poller_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        self._error_events.pop(unit_id, None)

        if exception:
            raise exception  # skipcq: PYL-E0702

        if not q:
            raise Exception("No query results")

        return await q[0].click(
            utils.get_chat_id(message) if isinstance(message, Message) else message,
            reply_to=(
                message.reply_to_msg_id if isinstance(message, Message) else None
            ),
        )
