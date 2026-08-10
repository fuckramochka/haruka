"""Structured adapter for common Hikka/FTG/GeekTG module contracts."""
from __future__ import annotations

import inspect
import logging
from typing import Any, Optional

from haruka.compat.hikka_runtime import hikka_base_class, install_hikka_runtime
from haruka.core.context import Context
from haruka.core.module import (
    BoundCommand,
    BoundWatcher,
    CommandSpec,
    Module,
    WatcherSpec,
)

logger = logging.getLogger(__name__)


def _is_hikka_module(obj: Any) -> bool:
    base = hikka_base_class()
    return inspect.isclass(obj) and issubclass(obj, base) and obj is not base


def _discover_commands(instance: Any) -> dict[str, Any]:
    commands = {}
    for name, member in inspect.getmembers(instance, predicate=callable):
        if hasattr(member, "__hikka_command__") or (
            name.endswith("cmd") and not name.startswith("_")
        ):
            command_name = name[:-3] if name.endswith("cmd") else name
            commands[command_name.rstrip("_").lower()] = member
    return commands


def _discover_watchers(instance: Any) -> list[Any]:
    return [
        member
        for name, member in inspect.getmembers(instance, predicate=callable)
        if hasattr(member, "__hikka_watcher__") or name == "watcher"
    ]


class HikkaAdapter(Module):
    """Expose a legacy module through native immutable handler records."""

    emoji = "🧩"

    def __init__(self, legacy: Any):
        super().__init__()
        self._legacy = legacy
        strings = getattr(legacy, "strings", {})
        if not isinstance(strings, dict):
            strings = {}
        self.name = strings.get("name") or type(legacy).__name__
        self.description = strings.get("_cls_doc") or (
            type(legacy).__doc__ or "Legacy compatibility module"
        ).strip()
        self._command_handlers = _discover_commands(legacy)
        self._watcher_handlers = _discover_watchers(legacy)
        self._bound_commands: list[BoundCommand] = []
        self._bound_watchers: list[BoundWatcher] = []
        self._build_records()

    def _build_records(self) -> None:
        for name, legacy_handler in self._command_handlers.items():
            async def run(ctx: Context, handler=legacy_handler):
                result = handler(ctx.message)
                if inspect.isawaitable(result):
                    await result

            run.__name__ = f"{name}_compat"
            metadata = getattr(legacy_handler, "__hikka_command__", {}) or {}
            spec = CommandSpec(
                name=name,
                aliases=list(metadata.get("alias", []) or metadata.get("aliases", []) or []),
                doc=(legacy_handler.__doc__ or f"[compat] {self.name}").strip(),
            )
            self._bound_commands.append(BoundCommand(name, spec, run, self))

        for legacy_handler in self._watcher_handlers:
            async def run_watcher(ctx: Context, handler=legacy_handler):
                result = handler(ctx.message)
                if inspect.isawaitable(result):
                    await result

            metadata = getattr(legacy_handler, "__hikka_watcher__", {}) or {}
            spec = WatcherSpec(
                incoming=not bool(metadata.get("out")),
                outgoing=bool(metadata.get("out", False)),
                only_groups=bool(metadata.get("only_groups", False)),
                only_private=bool(metadata.get("only_pm", False)),
            )
            self._bound_watchers.append(BoundWatcher(spec, run_watcher, self))

    def collect_commands(self) -> list[BoundCommand]:
        return list(self._bound_commands)

    def collect_watchers(self) -> list[BoundWatcher]:
        return list(self._bound_watchers)

    async def on_load(self) -> None:
        self._legacy._client = self.app.app
        self._legacy.client = self.app.app
        self._legacy.db = self.db
        self._legacy.inline = self.bot
        self._legacy.lookup = lambda name: (
            self.loader.modules.get(self.loader.resolve_module_name(name) or "")
        )
        for hook in ("client_ready", "on_load", "on_dlmod"):
            callback = getattr(self._legacy, hook, None)
            if callback is None:
                continue
            try:
                if hook == "client_ready":
                    try:
                        result = callback(self.app.app, self.db)
                    except TypeError:
                        result = callback()
                else:
                    result = callback()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Legacy hook %s failed for %s", hook, self.name)
                raise

    async def on_unload(self) -> None:
        callback = getattr(self._legacy, "on_unload", None)
        if callback:
            result = callback()
            if inspect.isawaitable(result):
                await result


def adapt_hikka_module(py_module) -> Optional[Module]:
    install_hikka_runtime()
    for _, obj in inspect.getmembers(py_module, inspect.isclass):
        if obj.__module__ != py_module.__name__ or not _is_hikka_module(obj):
            continue
        try:
            return HikkaAdapter(obj())
        except Exception:
            logger.exception("Could not adapt legacy module %s", obj.__name__)
            return None
    return None
