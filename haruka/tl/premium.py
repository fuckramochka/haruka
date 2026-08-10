"""Premium-account helpers.

Custom emoji in outgoing messages and custom reactions — features Kurigram's
high-level API only partially exposes. All helpers degrade gracefully on
non-premium accounts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from pyrogram.raw import functions, types

if TYPE_CHECKING:
    from haruka.core.client import HarukaClient

logger = logging.getLogger(__name__)


def custom_emoji_html(emoji_id: int, fallback: str) -> str:
    """HTML tag for a premium custom emoji with a plain-emoji fallback."""
    return f'<emoji id="{emoji_id}">{fallback}</emoji>'


class PremiumAPI:
    def __init__(self, client: "HarukaClient"):
        self._client = client

    @property
    def available(self) -> bool:
        return self._client.is_premium

    def emoji(self, emoji_id: Optional[int], fallback: str) -> str:
        """Premium emoji when possible, plain fallback otherwise."""
        if emoji_id and self.available:
            return custom_emoji_html(emoji_id, fallback)
        return fallback

    async def react(
        self,
        chat_id: int,
        message_id: int,
        emoji: str = "",
        custom_emoji_id: Optional[int] = None,
        big: bool = False,
    ) -> bool:
        """Send a reaction; supports premium custom-emoji reactions."""
        reaction: list
        if custom_emoji_id is not None and self.available:
            reaction = [types.ReactionCustomEmoji(document_id=custom_emoji_id)]
        elif emoji:
            reaction = [types.ReactionEmoji(emoticon=emoji)]
        else:
            reaction = []  # remove reaction

        try:
            peer = await self._client.app.resolve_peer(chat_id)
            await self._client.invoke_safe(
                functions.messages.SendReaction(
                    peer=peer,
                    msg_id=message_id,
                    reaction=reaction,
                    big=big,
                )
            )
            return True
        except Exception:
            logger.debug("reaction failed", exc_info=True)
            return False
