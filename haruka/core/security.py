"""Roles, permissions and rate limiting.

Every command carries a required role. The dispatcher consults
:class:`SecurityManager` before executing anything. All privileged actions
are written to the audit log.
"""

from __future__ import annotations

import logging
import re
import time
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from haruka.core.database import Database

logger = logging.getLogger(__name__)

# Patterns for secrets that must never leak into chat output.
_SECRET_PATTERNS = [
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),           # bot tokens
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{20,}\b"),          # api keys
    re.compile(r"\b1[A-Za-z0-9+/=]{200,}\b"),                 # string sessions
    re.compile(r"(?i)\b(api_hash|api_id|password)\s*=\s*\S+"),
]


def mask_secrets(text: str) -> str:
    """Replace anything that looks like a credential with a mask."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[...token hidden by haruka...]", text)
    return text


class Role(IntEnum):
    EVERYONE = 0
    SUPPORT = 10
    SUDO = 20
    OWNER = 30


class RateLimiter:
    """Sliding-window rate limiter per (user, command)."""

    def __init__(self, max_hits: int = 6, window: float = 10.0):
        self.max_hits = max_hits
        self.window = window
        self._hits: dict[tuple[int, str], list[float]] = {}

    def allow(self, user_id: int, command: str) -> bool:
        now = time.monotonic()
        if len(self._hits) > 4096:
            self._hits = {
                key: values
                for key, values in self._hits.items()
                if values and now - values[-1] < self.window
            }
        key = (user_id, command)
        hits = [t for t in self._hits.get(key, []) if now - t < self.window]
        if len(hits) >= self.max_hits:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


class SecurityManager:
    """Resolves user roles and enforces access to commands."""

    OWNER = "security.owner"
    SUDO = "security.sudo_users"
    SUPPORT = "security.support_users"

    def __init__(self, db: "Database"):
        self._db = db
        self._owner_id: Optional[int] = None
        self.rate_limiter = RateLimiter()

    def set_owner(self, user_id: int) -> None:
        self._owner_id = user_id

    @property
    def owner_id(self) -> Optional[int]:
        return self._owner_id

    def role_of(self, user_id: Optional[int]) -> Role:
        if user_id is None:
            return Role.EVERYONE
        if user_id == self._owner_id:
            return Role.OWNER
        if user_id in self._db.get("core", self.SUDO, []):
            return Role.SUDO
        if user_id in self._db.get("core", self.SUPPORT, []):
            return Role.SUPPORT
        return Role.EVERYONE

    def check(self, user_id: Optional[int], required: Role) -> bool:
        return self.role_of(user_id) >= required

    async def grant(self, user_id: int, role: Role) -> None:
        key = self.SUDO if role == Role.SUDO else self.SUPPORT
        users = list(self._db.get("core", key, []))
        if user_id not in users:
            users.append(user_id)
            await self._db.set("core", key, users)
            await self._db.audit("security.grant", f"{role.name} -> {user_id}")

    async def revoke(self, user_id: int) -> None:
        for key in (self.SUDO, self.SUPPORT):
            users = list(self._db.get("core", key, []))
            if user_id in users:
                users.remove(user_id)
                await self._db.set("core", key, users)
        await self._db.audit("security.revoke", str(user_id))

    def list_privileged(self) -> dict[str, list[int]]:
        return {
            "owner": [self._owner_id] if self._owner_id else [],
            "sudo": self._db.get("core", self.SUDO, []),
            "support": self._db.get("core", self.SUPPORT, []),
        }
