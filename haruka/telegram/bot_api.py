from __future__ import annotations

"""Low-level Telegram Bot API transport.

This adapter deliberately exposes API-shaped payloads instead of turning Haruka
into a bot. Applications opt in to it; the core engine remains transport neutral.
Unknown fields are preserved so a newer Bot API can be used before this package
ships typed wrappers.
"""

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import aiohttp

Json = dict[str, Any]


class TelegramAPIError(RuntimeError):
    def __init__(self, method: str, status: int, description: str, parameters: Json | None = None):
        super().__init__(f"Telegram {method} failed ({status}): {description}")
        self.method = method
        self.status = status
        self.description = description
        self.parameters = parameters or {}


@dataclass(slots=True)
class BotAPIConfig:
    token: str
    api_base: str = "https://api.telegram.org"
    request_timeout: float = 65.0
    max_retries: int = 3


class BotAPIClient:
    """Async Bot API 10.1-capable client with retries and forward compatibility."""

    def __init__(self, config: BotAPIConfig, session: aiohttp.ClientSession | None = None):
        self.config = config
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "BotAPIClient":
        await self.open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def open(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.request_timeout))
            self._owns_session = True

    async def close(self) -> None:
        if self._session and self._owns_session:
            await self._session.close()
        self._session = None

    async def call(self, method: str, payload: Mapping[str, Any] | None = None) -> Any:
        await self.open()
        assert self._session is not None
        url = f"{self.config.api_base.rstrip('/')}/bot{self.config.token}/{method}"
        body = {key: value for key, value in (payload or {}).items() if value is not None}
        for attempt in range(self.config.max_retries + 1):
            try:
                async with self._session.post(url, json=body) as response:
                    data = await response.json(content_type=None)
                    if response.status == 429 and attempt < self.config.max_retries:
                        delay = float(data.get("parameters", {}).get("retry_after", 1))
                        await asyncio.sleep(min(delay, 30.0))
                        continue
                    if response.status >= 500 and attempt < self.config.max_retries:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                    if not data.get("ok"):
                        raise TelegramAPIError(method, response.status, str(data.get("description", "unknown error")), data.get("parameters"))
                    return data.get("result")
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt >= self.config.max_retries:
                    raise TelegramAPIError(method, 0, str(exc)) from exc
                await asyncio.sleep(0.5 * (2**attempt))
        raise AssertionError("unreachable")

    async def get_updates(self, *, offset: int | None = None, timeout: int = 50, allowed_updates: Sequence[str] | None = None) -> list[Json]:
        result = await self.call("getUpdates", {"offset": offset, "timeout": timeout, "allowed_updates": list(allowed_updates) if allowed_updates else None})
        return list(result or [])

    async def iter_updates(self, *, allowed_updates: Sequence[str] | None = None) -> AsyncIterator[Json]:
        offset: int | None = None
        while True:
            updates = await self.get_updates(offset=offset, allowed_updates=allowed_updates)
            for update in updates:
                offset = int(update["update_id"]) + 1
                yield update

    async def send_message(self, chat_id: int | str, text: str, **options: Any) -> Json:
        return await self.call("sendMessage", {"chat_id": chat_id, "text": text, **options})

    async def send_message_draft(self, chat_id: int | str, draft_id: int, text: str, **options: Any) -> Any:
        return await self.call("sendMessageDraft", {"chat_id": chat_id, "draft_id": draft_id, "text": text, **options})

    async def send_rich_message(self, chat_id: int | str, rich_message: Mapping[str, Any], **options: Any) -> Json:
        return await self.call("sendRichMessage", {"chat_id": chat_id, "rich_message": dict(rich_message), **options})

    async def send_rich_message_draft(self, chat_id: int | str, draft_id: int, rich_message: Mapping[str, Any], **options: Any) -> Any:
        return await self.call("sendRichMessageDraft", {"chat_id": chat_id, "draft_id": draft_id, "rich_message": dict(rich_message), **options})

    async def answer_guest_query(self, guest_query_id: str, *, text: str | None = None, rich_message: Mapping[str, Any] | None = None, **options: Any) -> Json:
        return await self.call("answerGuestQuery", {"guest_query_id": guest_query_id, "text": text, "rich_message": dict(rich_message) if rich_message else None, **options})

    async def send_checklist(self, business_connection_id: str, chat_id: int | str, checklist: Mapping[str, Any], **options: Any) -> Json:
        return await self.call("sendChecklist", {"business_connection_id": business_connection_id, "chat_id": chat_id, "checklist": dict(checklist), **options})

    async def edit_message_checklist(self, business_connection_id: str, chat_id: int | str, message_id: int, checklist: Mapping[str, Any], **options: Any) -> Json:
        return await self.call("editMessageChecklist", {"business_connection_id": business_connection_id, "chat_id": chat_id, "message_id": message_id, "checklist": dict(checklist), **options})

    async def delete_message_reaction(self, chat_id: int | str, message_id: int, reaction: Mapping[str, Any]) -> bool:
        return bool(await self.call("deleteMessageReaction", {"chat_id": chat_id, "message_id": message_id, "reaction": dict(reaction)}))

    async def delete_all_message_reactions(self, chat_id: int | str, message_id: int) -> bool:
        return bool(await self.call("deleteAllMessageReactions", {"chat_id": chat_id, "message_id": message_id}))

    async def send_poll(self, chat_id: int | str, question: str, options: Sequence[Mapping[str, Any]], *, media: Mapping[str, Any] | None = None, explanation_media: Mapping[str, Any] | None = None, members_only: bool | None = None, **extra: Any) -> Json:
        return await self.call("sendPoll", {"chat_id": chat_id, "question": question, "options": [dict(item) for item in options], "media": dict(media) if media else None, "explanation_media": dict(explanation_media) if explanation_media else None, "members_only": members_only, **extra})

    async def read_business_message(self, business_connection_id: str, chat_id: int | str, message_id: int) -> bool:
        return bool(await self.call("readBusinessMessage", {"business_connection_id": business_connection_id, "chat_id": chat_id, "message_id": message_id}))

    async def delete_business_messages(self, business_connection_id: str, message_ids: Sequence[int]) -> bool:
        return bool(await self.call("deleteBusinessMessages", {"business_connection_id": business_connection_id, "message_ids": list(message_ids)}))
