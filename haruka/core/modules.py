from __future__ import annotations

import asyncio
import inspect
import re
import shlex
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from haruka.core.security import Capability, SecurityPolicy
from haruka.domain import IncomingMessage

CommandHandler = Callable[["CommandContext"], Awaitable[str | None] | str | None]
_COMMAND = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    name: str
    version: str
    engine_api: str = "1"
    description: str = ""
    capabilities: frozenset[Capability] = frozenset()
    dependencies: tuple[str, ...] = ()
    source_digest: str | None = None

    def __post_init__(self) -> None:
        if not _COMMAND.fullmatch(self.name):
            raise ValueError(f"Invalid module name: {self.name}")


@dataclass(frozen=True, slots=True)
class CommandSpec:
    name: str
    module: str
    description: str = ""
    aliases: tuple[str, ...] = ()
    owner_only: bool = False
    timeout: float = 20.0


@dataclass(slots=True)
class CommandContext:
    message: IncomingMessage
    raw: object
    command: str
    args: list[str]
    services: dict[str, Any]


class EngineModule(Protocol):
    manifest: ModuleManifest
    async def start(self, services: dict[str, Any]) -> None: ...
    async def stop(self) -> None: ...


@dataclass(slots=True)
class ModuleHealth:
    commands: int = 0
    failures: int = 0
    last_error: str | None = None


class ModuleRegistry:
    """Versioned module SDK with dependency, capability and command isolation."""

    def __init__(self, policy: SecurityPolicy, *, prefix: str = ".") -> None:
        self.policy = policy
        self.prefix = prefix
        self.modules: dict[str, EngineModule] = {}
        self.commands: dict[str, tuple[CommandSpec, CommandHandler]] = {}
        self.health: dict[str, ModuleHealth] = {}
        self.services: dict[str, Any] = {}

    def provide(self, name: str, value: Any) -> None:
        self.services[name] = value

    def register_module(self, module: EngineModule) -> None:
        manifest = module.manifest
        if manifest.name in self.modules:
            raise ValueError(f"Duplicate module: {manifest.name}")
        missing = [name for name in manifest.dependencies if name not in self.modules]
        if missing:
            raise ValueError(f"{manifest.name} has missing dependencies: {', '.join(missing)}")
        self.policy.validate_requested(manifest.name, manifest.capabilities)
        self.modules[manifest.name] = module
        self.health[manifest.name] = ModuleHealth()

    def command(self, spec: CommandSpec) -> Callable[[CommandHandler], CommandHandler]:
        if spec.module not in self.modules:
            raise LookupError(f"Register module before commands: {spec.module}")
        names = (spec.name, *spec.aliases)
        for name in names:
            if not _COMMAND.fullmatch(name):
                raise ValueError(f"Invalid command: {name}")
            if name in self.commands:
                raise ValueError(f"Command collision: {name}")

        def decorator(handler: CommandHandler) -> CommandHandler:
            for name in names:
                self.commands[name] = (spec, handler)
            return handler
        return decorator

    async def start(self) -> None:
        for module in self.modules.values():
            await module.start(dict(self.services))

    async def stop(self) -> None:
        for module in reversed(tuple(self.modules.values())):
            await module.stop()

    async def dispatch(self, message: IncomingMessage, raw: object, *, is_owner: bool = False) -> str | None:
        if not message.text.startswith(self.prefix):
            return None
        try:
            parts = shlex.split(message.text[len(self.prefix):])
        except ValueError:
            return None
        if not parts:
            return None
        entry = self.commands.get(parts[0].casefold())
        if not entry:
            return None
        spec, handler = entry
        if spec.owner_only and not is_owner:
            raise PermissionError("Owner-only command")
        state = self.health[spec.module]
        state.commands += 1
        context = CommandContext(message, raw, spec.name, parts[1:], dict(self.services))
        try:
            result = handler(context)
            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout=spec.timeout)
            return result
        except Exception as exc:
            state.failures += 1
            state.last_error = f"{type(exc).__name__}: {exc}"
            raise

    def command_catalog(self) -> list[CommandSpec]:
        unique = {id(value[0]): value[0] for value in self.commands.values()}
        return sorted(unique.values(), key=lambda item: (item.module, item.name))
