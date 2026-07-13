"""Telegram-backed runtime log delivery without blocking the logging thread."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque


class TelegramLogHandler(logging.Handler):
    def __init__(self, client, chat_id: int):
        super().__init__(logging.WARNING)
        self.client = client
        self.chat_id = chat_id
        self.loop = asyncio.get_running_loop()
        self.recent: deque[tuple[str, float]] = deque(maxlen=30)
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s\n%(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(("pyrogram", "haruka.runtime_logging")):
            return
        try:
            text = self.format(record)
            now = time.monotonic()
            signature = f"{record.name}:{record.levelno}:{record.getMessage()}"
            if any(item == signature and now - ts < 30 for item, ts in self.recent):
                return
            self.recent.append((signature, now))
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._send(text[-3500:]))
            )
        except Exception:
            self.handleError(record)

    async def _send(self, text: str) -> None:
        try:
            import html
            await self.client.send_message(
                self.chat_id,
                "⚠️ <b>Haruka runtime</b>\n<pre>" + html.escape(text) + "</pre>",
            )
        except Exception:
            pass


async def ensure_log_chat(app) -> int | None:
    chat_id = app.db.get("core", "log_chat_id")
    if chat_id:
        try:
            await app.client.app.get_chat(chat_id)
            return int(chat_id)
        except Exception:
            await app.db.set("core", "log_chat_id", None)

    try:
        chat = await app.client.app.create_channel(
            "Haruka Engine",
            "Private Haruka runtime log and service channel. Do not share it.",
        )
        chat_id = int(chat.id)
        await app.db.set("core", "log_chat_id", chat_id)
        await app.client.app.send_message(
            chat_id,
            "✦ <b>HARUKA ENGINE LOG</b>\n"
            "<blockquote>This private channel stores startup reports, warnings and errors. "
            "Haruka created it automatically so diagnostics are never lost in the terminal.</blockquote>",
        )
        return chat_id
    except Exception:
        logging.getLogger(__name__).exception("Could not create the Haruka log channel")
        return None


def install_telegram_logging(app, chat_id: int) -> None:
    if getattr(app, "telegram_log_handler", None) is not None:
        return
    handler = TelegramLogHandler(app.client.app, chat_id)
    logging.getLogger().addHandler(handler)
    app.telegram_log_handler = handler
