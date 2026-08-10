"""Kurigram client wrapper.

Kurigram (a maintained Pyrogram fork) installs under the ``pyrogram``
namespace. This wrapper owns session creation, interactive login,
flood-wait-aware invocation and reconnect logic, so nothing else in the
codebase talks to raw ``pyrogram.Client`` directly.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from pyrogram import Client
from pyrogram.errors import FloodWait

logger = logging.getLogger(__name__)


class HarukaClient:
    """Thin lifecycle wrapper around a Kurigram :class:`pyrogram.Client`."""

    def __init__(
        self,
        session_name: str,
        api_id: int,
        api_hash: str,
        workdir: Path,
    ):
        workdir.mkdir(parents=True, exist_ok=True)
        self.app = Client(
            name=session_name,
            api_id=api_id,
            api_hash=api_hash,
            workdir=str(workdir),
            sleep_threshold=30,  # auto-sleep on short flood waits
        )
        self._me = None

    # -- lifecycle -----------------------------------------------------

    async def start(self) -> None:
        await self.app.start()
        self._me = await self.app.get_me()
        logger.info(
            "Signed in as %s (id=%s, premium=%s)",
            self._me.first_name,
            self._me.id,
            bool(getattr(self._me, "is_premium", False)),
        )

    async def stop(self) -> None:
        try:
            await self.app.stop()
        except ConnectionError:
            pass  # already disconnected

    @property
    def me(self):
        return self._me

    @property
    def is_premium(self) -> bool:
        return bool(getattr(self._me, "is_premium", False))

    # -- safe invocation --------------------------------------------------

    async def invoke_safe(self, raw_function: Any, retries: int = 3) -> Any:
        """Invoke a raw TL function with flood-wait retries."""
        for attempt in range(retries):
            try:
                return await self.app.invoke(raw_function)
            except FloodWait as e:
                wait = int(getattr(e, "value", 5) or 5)
                if attempt == retries - 1 or wait > 300:
                    raise
                logger.warning("FloodWait %ss on %s, retrying", wait, type(raw_function).__name__)
                await asyncio.sleep(wait + 1)
        raise RuntimeError("unreachable")
