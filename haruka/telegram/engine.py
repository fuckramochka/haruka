from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Awaitable, Callable

from telethon import TelegramClient, events
from telethon.tl.custom import Message

from haruka.config.settings import Settings
from haruka.domain import IncomingMessage

logger = logging.getLogger(__name__)
MessageHandler = Callable[[IncomingMessage, Message], Awaitable[None]]


class TelegramEngine:
    """Telethon/MTProto adapter.

    This is an adapter, not the Haruka product. Products may replace it with a
    Bot API, TDLib, mock, webhook, or multi-account transport.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = TelegramClient(str(settings.telegram_session), settings.telegram_api_id, settings.telegram_api_hash)
        self._self_id: int | None = None
        self._handler: MessageHandler | None = None

    async def start(self, handler: MessageHandler) -> None:
        self._handler = handler
        await self.client.start(bot_token=self.settings.telegram_bot_token) if self.settings.telegram_bot_token else await self.client.start()
        me = await self.client.get_me()
        self._self_id = int(me.id)
        logger.info("Telegram connected as %s", getattr(me, "username", None) or me.id)

        @self.client.on(events.NewMessage(incoming=True))
        async def on_message(event: events.NewMessage.Event) -> None:
            try:
                message = await self._to_incoming(event.message)
                if message.text and self._chat_allowed(message.chat_id):
                    await handler(message, event.message)
            except Exception:
                logger.exception("Incoming Telegram event failed")

    def _chat_allowed(self, chat_id: int) -> bool:
        return not self.settings.allowed_chat_ids or chat_id in self.settings.allowed_chat_ids

    async def run_forever(self) -> None:
        await self.client.run_until_disconnected()

    async def close(self) -> None:
        await self.client.disconnect()

    async def send_message(self, raw_message: Message, text: str) -> None:
        if self.settings.dry_run:
            logger.info("DRY RUN reply to %s: %s", raw_message.chat_id, text)
            return
        await raw_message.reply(text)

    async def send_chat_message(self, chat_id: int, text: str, *, reply_to: int | None = None) -> None:
        if self.settings.dry_run:
            logger.info("DRY RUN send to %s: %s", chat_id, text)
            return
        await self.client.send_message(chat_id, text, reply_to=reply_to)

    async def send_reaction(self, raw_message: Message, reaction: str) -> None:
        if self.settings.dry_run:
            logger.info("DRY RUN reaction to %s: %s", raw_message.id, reaction)
            return
        try:
            await self.client.send_reaction(raw_message.peer_id, raw_message.id, reaction)
        except Exception as exc:
            logger.debug("Reaction unavailable: %s", exc)

    async def send_file(self, chat_id: int, path: str, caption: str | None = None, **options: object) -> None:
        if self.settings.dry_run:
            logger.info("DRY RUN file to %s: %s", chat_id, path)
            return
        await self.client.send_file(chat_id, path, caption=caption, **options)

    async def send_photo(self, chat_id: int, path: str, caption: str | None = None) -> None:
        await self.send_file(chat_id, path, caption)

    async def send_sticker(self, chat_id: int, path_or_id: str) -> None:
        await self.send_file(chat_id, path_or_id, force_document=False)

    async def load_recent_texts(self, chat_id: int, limit: int = 500) -> list[str]:
        texts = [message.text async for message in self.client.iter_messages(chat_id, limit=limit) if message.text]
        return list(reversed(texts))

    async def scan_recent_messages(self, limit_per_chat: int = 5) -> list[IncomingMessage]:
        result: list[IncomingMessage] = []
        count = 0
        async for dialog in self.client.iter_dialogs():
            if count >= self.settings.max_scan_dialogs:
                break
            chat_id = int(getattr(dialog, "id", 0))
            if not chat_id or not self._chat_allowed(chat_id):
                continue
            count += 1
            async for message in self.client.iter_messages(dialog.entity, limit=limit_per_chat):
                if message.text and not message.out:
                    result.append(await self._to_incoming(message))
        return result

    async def known_dialogs(self) -> list[tuple[int, str | None]]:
        dialogs: list[tuple[int, str | None]] = []
        async for dialog in self.client.iter_dialogs():
            chat_id = int(getattr(dialog, "id", 0))
            if chat_id and self._chat_allowed(chat_id):
                dialogs.append((chat_id, getattr(dialog, "title", None) or getattr(dialog.entity, "title", None)))
            if len(dialogs) >= self.settings.max_scan_dialogs:
                break
        return dialogs

    async def _to_incoming(self, message: Message) -> IncomingMessage:
        chat, sender = await message.get_chat(), await message.get_sender()
        text = message.raw_text or ""
        lower = text.casefold()
        is_reply_to_haruka = False
        if message.reply_to_msg_id and self._self_id is not None:
            try:
                reply = await message.get_reply_message()
                is_reply_to_haruka = bool(reply and reply.sender_id == self._self_id)
            except Exception:
                logger.debug("Reply target could not be resolved", exc_info=True)
        thread_id = getattr(getattr(message, "reply_to", None), "reply_to_top_id", None)
        return IncomingMessage(
            message_id=int(message.id), chat_id=int(message.chat_id or 0),
            sender_id=int(message.sender_id) if message.sender_id is not None else None,
            chat_title=getattr(chat, "title", None), sender_name=self._display_name(sender),
            sender_username=getattr(sender, "username", None), text=text,
            is_private=bool(message.is_private), is_reply_to_haruka=is_reply_to_haruka,
            mentioned_haruka=f"@{self.settings.username.casefold()}" in lower or self.settings.name.casefold() in lower,
            created_at=message.date.astimezone(UTC) if message.date else datetime.now(UTC),
            thread_id=int(thread_id) if thread_id is not None else None,
        )

    @staticmethod
    def _display_name(sender: object) -> str | None:
        if sender is None:
            return None
        return " ".join(filter(None, [getattr(sender, "first_name", None), getattr(sender, "last_name", None)])) or getattr(sender, "title", None)
