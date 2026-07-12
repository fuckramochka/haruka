from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from haruka.domain import IncomingMessage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EngineContext:
    services: dict[str, Any] = field(default_factory=dict)

    def require(self, name: str) -> Any:
        try:
            return self.services[name]
        except KeyError as exc:
            raise LookupError(f"Engine service is not registered: {name}") from exc


class Plugin(Protocol):
    name: str

    async def start(self, context: EngineContext) -> None: ...
    async def stop(self) -> None: ...
    async def on_message(self, message: IncomingMessage, raw: object) -> None: ...


class PluginManager:
    """Isolated extension surface for products built on the Haruka engine."""

    def __init__(self, context: EngineContext):
        self.context = context
        self._plugins: list[Plugin] = []

    def register(self, plugin: Plugin) -> None:
        if any(item.name == plugin.name for item in self._plugins):
            raise ValueError(f"Duplicate plugin: {plugin.name}")
        self._plugins.append(plugin)

    async def start(self) -> None:
        for plugin in self._plugins:
            await plugin.start(self.context)

    async def dispatch_message(self, message: IncomingMessage, raw: object) -> None:
        results = await asyncio.gather(*(plugin.on_message(message, raw) for plugin in self._plugins), return_exceptions=True)
        for plugin, result in zip(self._plugins, results, strict=True):
            if isinstance(result, BaseException):
                logger.exception("Plugin %s failed", plugin.name, exc_info=result)

    async def stop(self) -> None:
        for plugin in reversed(self._plugins):
            try:
                await plugin.stop()
            except Exception:
                logger.exception("Plugin %s failed to stop", plugin.name)
