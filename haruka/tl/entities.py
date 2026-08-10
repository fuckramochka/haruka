"""Cached entity resolution.

Kurigram resolves peers on every call; this cache keeps recently used
users/chats in memory with TTL so hot paths (watchers, triggers) don't
hammer the API — the modern replacement for the old ``tl_cache``.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from haruka.core.client import HarukaClient


class EntityCache:
    def __init__(self, client: "HarukaClient", ttl: float = 300.0, max_size: int = 512):
        self._client = client
        self._ttl = ttl
        self._max_size = max_size
        self._users: dict[Union[int, str], tuple[float, Any]] = {}
        self._chats: dict[Union[int, str], tuple[float, Any]] = {}

    def _fresh(self, store: dict, key) -> Optional[Any]:
        entry = store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del store[key]
            return None
        return value

    def _put(self, store: dict, key, value) -> None:
        if len(store) >= self._max_size:
            # Evict oldest entry.
            oldest = min(store, key=lambda k: store[k][0])
            del store[oldest]
        store[key] = (time.monotonic(), value)

    async def user(self, user_id: Union[int, str]) -> Any:
        cached = self._fresh(self._users, user_id)
        if cached is not None:
            return cached
        user = await self._client.app.get_users(user_id)
        self._put(self._users, user_id, user)
        if user.username:
            self._put(self._users, user.username.lower(), user)
        self._put(self._users, user.id, user)
        return user

    async def chat(self, chat_id: Union[int, str]) -> Any:
        cached = self._fresh(self._chats, chat_id)
        if cached is not None:
            return cached
        chat = await self._client.app.get_chat(chat_id)
        self._put(self._chats, chat_id, chat)
        if getattr(chat, "username", None):
            self._put(self._chats, chat.username.lower(), chat)
        self._put(self._chats, chat.id, chat)
        return chat

    def invalidate(self, key: Union[int, str]) -> None:
        self._users.pop(key, None)
        self._chats.pop(key, None)

    def clear(self) -> None:
        self._users.clear()
        self._chats.clear()
