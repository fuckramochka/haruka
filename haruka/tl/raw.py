"""Ergonomic access to Kurigram's raw TL layer.

Wraps ``pyrogram.raw`` so modules can make low-level calls in one line with
flood-wait handling from :class:`HarukaClient` — the escape hatch for
anything the high-level API does not cover.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pyrogram.raw import functions, types  # re-exported for modules

if TYPE_CHECKING:
    from haruka.core.client import HarukaClient

logger = logging.getLogger(__name__)

__all__ = ["RawAPI", "functions", "types"]


class RawAPI:
    """Facade over raw TL invocation.

    Example::

        raw = RawAPI(client)
        full = await raw.call(functions.users.GetFullUser(
            id=await raw.resolve_input_user(user_id),
        ))
    """

    def __init__(self, client: "HarukaClient"):
        self._client = client

    async def call(self, tl_function: Any, retries: int = 3) -> Any:
        """Invoke any raw TL function with flood-wait retries."""
        return await self._client.invoke_safe(tl_function, retries=retries)

    # -- input peer helpers (the most common raw-API pain point) -----------

    async def resolve_input_peer(self, chat_id: int | str) -> Any:
        return await self._client.app.resolve_peer(chat_id)

    async def resolve_input_user(self, user_id: int | str) -> Any:
        peer = await self._client.app.resolve_peer(user_id)
        if not isinstance(peer, (types.InputPeerUser, types.InputPeerSelf)):
            raise ValueError(f"{user_id} is not a user")
        if isinstance(peer, types.InputPeerSelf):
            me = self._client.me
            return types.InputUserSelf() if me is None else types.InputUserSelf()
        return types.InputUser(user_id=peer.user_id, access_hash=peer.access_hash)

    # -- frequently needed raw calls ---------------------------------------

    async def get_full_user(self, user_id: int | str) -> Any:
        return await self.call(
            functions.users.GetFullUser(id=await self.resolve_input_user(user_id))
        )

    async def get_common_chats(self, user_id: int | str, limit: int = 100) -> Any:
        return await self.call(
            functions.messages.GetCommonChats(
                user_id=await self.resolve_input_user(user_id),
                max_id=0,
                limit=limit,
            )
        )

    async def get_authorizations(self) -> Any:
        """Active sessions on the account (used by the security module)."""
        return await self.call(functions.account.GetAuthorizations())

    async def reset_authorization(self, auth_hash: int) -> Any:
        """Terminate a session by hash."""
        return await self.call(functions.account.ResetAuthorization(hash=auth_hash))
