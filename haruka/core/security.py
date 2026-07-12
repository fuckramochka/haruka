from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Capability(StrEnum):
    READ_MESSAGES = "telegram.read_messages"
    SEND_MESSAGES = "telegram.send_messages"
    MANAGE_CHATS = "telegram.manage_chats"
    ACCESS_MEMORY = "haruka.memory"
    MODIFY_MEMORY = "haruka.memory.write"
    NETWORK = "system.network"
    FILE_READ = "system.file.read"
    FILE_WRITE = "system.file.write"
    PROCESS = "system.process"
    SECRETS = "system.secrets"


SAFE_DEFAULTS = frozenset({Capability.READ_MESSAGES, Capability.ACCESS_MEMORY})
DANGEROUS = frozenset({Capability.MANAGE_CHATS, Capability.FILE_WRITE, Capability.PROCESS, Capability.SECRETS})


class CapabilityDenied(PermissionError):
    pass


@dataclass(slots=True)
class SecurityPolicy:
    """Deny-by-default module capabilities; dangerous rights need explicit trust."""

    grants: dict[str, frozenset[Capability]] = field(default_factory=dict)
    trusted_modules: frozenset[str] = field(default_factory=frozenset)

    def capabilities_for(self, module: str) -> frozenset[Capability]:
        return self.grants.get(module, SAFE_DEFAULTS)

    def require(self, module: str, capability: Capability) -> None:
        if capability not in self.capabilities_for(module):
            raise CapabilityDenied(f"{module!r} is not allowed to use {capability.value}")
        if capability in DANGEROUS and module not in self.trusted_modules:
            raise CapabilityDenied(f"{module!r} must be trusted for {capability.value}")

    def validate_requested(self, module: str, requested: frozenset[Capability]) -> None:
        for capability in requested:
            self.require(module, capability)


def source_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(path.rglob("*.py")):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def verify_digest(actual: str, expected: str) -> bool:
    return hmac.compare_digest(actual.casefold(), expected.casefold())
