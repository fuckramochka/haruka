"""Best-effort BotFather provisioning for the companion inline bot."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from haruka.core.app import Application

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b")


class ProvisioningError(RuntimeError):
    """BotFather could not provision a companion bot automatically."""


def _sanitize(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum() or ch == "_")


def _fit_username(base: str) -> str:
    base = _sanitize(base).strip("_")
    if not base.endswith("bot"):
        if base.endswith("_"):
            base += "bot"
        else:
            base += "_bot"
    if len(base) < 5:
        base = f"haruka_{base}bot"
    return base[:32].rstrip("_")


class BotFatherProvisioner:
    def __init__(self, app: "Application"):
        self.app = app
        self.client = app.client.app
        self.owner = app.client.me

    async def provision(self) -> tuple[str, str]:
        await self._reset_dialog()
        opening = await self._ask("/newbot")
        lower = opening.lower()
        if "too many" in lower or "limit" in lower:
            raise ProvisioningError("BotFather says this account already has too many bots.")
        if "bot" not in lower and "name" not in lower:
            await self._reset_dialog()
            opening = await self._ask("/newbot")
        await self._ask(self._display_name())
        for candidate in self._username_candidates():
            reply = await self._ask(candidate)
            token = TOKEN_RE.search(reply or "")
            if token:
                username = candidate.lstrip("@")
                await self._configure_bot(username)
                return token.group(0), username
            lowered = (reply or "").lower()
            if any(word in lowered for word in ("sorry", "taken", "invalid", "already", "short", "long")):
                continue
        raise ProvisioningError("BotFather did not accept any generated usernames.")

    def _display_name(self) -> str:
        first = getattr(self.owner, "first_name", None) or "Owner"
        return f"Haruka Control {first}"[:64]

    def _username_candidates(self) -> list[str]:
        owner_username = getattr(self.owner, "username", None) or ""
        first = getattr(self.owner, "first_name", None) or "owner"
        owner_id = getattr(self.owner, "id", 0)
        bases = [
            f"haruka_{owner_username}_bot",
            f"haruka_{first}_{owner_id}_bot",
            f"harukaengine_{owner_id}_bot",
            f"haruka{owner_id}bot",
        ]
        seen = set()
        candidates = []
        for base in bases:
            candidate = _fit_username(base)
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)
        return candidates

    async def _latest_message_id(self) -> int:
        async for message in self.client.get_chat_history("BotFather", limit=1):
            return int(message.id)
        return 0

    async def _wait_for_reply(self, after_id: int, timeout: float = 20.0) -> str:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            async for message in self.client.get_chat_history("BotFather", limit=10):
                if int(message.id) <= after_id:
                    continue
                if getattr(message, "outgoing", False):
                    continue
                return message.text or message.caption or ""
            await asyncio.sleep(0.6)
        raise ProvisioningError("BotFather did not reply in time.")

    async def _ask(self, text: str, timeout: float = 20.0) -> str:
        marker = await self._latest_message_id()
        await self.client.send_message("BotFather", text)
        return await self._wait_for_reply(marker, timeout=timeout)

    async def _reset_dialog(self) -> None:
        try:
            await self._ask("/cancel", timeout=10.0)
        except Exception:
            logger.debug("BotFather dialog reset skipped", exc_info=True)

    async def _configure_bot(self, username: str) -> None:
        try:
            await self._ask("/setinline")
            await self._ask(f"@{username}")
            await self._ask("Open Haruka Control Center")
        except Exception:
            logger.exception("Could not enable inline mode for @%s", username)
        try:
            await self._ask("/setdescription")
            await self._ask(f"@{username}")
            await self._ask("Haruka companion bot for Control Center and inline UI.")
        except Exception:
            logger.debug("Could not set bot description", exc_info=True)
        try:
            await self._ask("/setabouttext")
            await self._ask(f"@{username}")
            await self._ask("Haruka engine companion")
        except Exception:
            logger.debug("Could not set about text", exc_info=True)


async def provision_inline_bot(app: "Application") -> tuple[str, str]:
    provisioner = BotFatherProvisioner(app)
    token, username = await provisioner.provision()
    await app.db.set_many(
        "core",
        {
            "inline_bot_token": token,
            "inline_bot_username": username,
            "inline_bootstrapped": False,
        },
    )
    return token, username


async def ensure_inline_bot_token(app: "Application") -> tuple[str | None, str | None, bool]:
    token = app.db.get("core", "inline_bot_token")
    username = app.db.get("core", "inline_bot_username")
    if token:
        return token, username, False
    try:
        token, username = await provision_inline_bot(app)
        return token, username, True
    except Exception:
        logger.exception("Automatic companion-bot provisioning failed")
        return None, None, False
