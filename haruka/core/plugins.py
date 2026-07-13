"""The plugin system: user-installable extensions that shape the *behaviour*
of the userbot itself.

Modules add commands (features that talk to Telegram). **Plugins are
different**: they hook into the engine's own lifecycle and can change how the
userbot behaves — rewrite every outgoing message, veto or audit commands,
react to incoming traffic, and so on. A user can drop a plugin in and
instantly customise the bot without writing a single command.

A plugin is a subclass of :class:`Plugin` that overrides one or more hooks:

* ``before_command(ctx)`` — return ``False`` to veto a command.
* ``after_command(ctx)`` — run something after a command completes.
* ``transform_outgoing(text, ctx)`` — return modified text for every reply.
* ``on_incoming(message)`` — observe every incoming message.
* ``on_error(ctx, exc)`` — react to command failures.

Hooks are all optional and always fail-soft: a raising plugin is logged and
skipped, never taking the engine down. Plugins run in ascending ``priority``
order and each keeps db-backed options (see :attr:`Plugin.options`).
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import pkgutil
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

logger = logging.getLogger(__name__)

_BUILTIN_PACKAGE = "haruka.plugins"

if TYPE_CHECKING:
    from haruka.core.context import Context


class Plugin:
    """Base class for behaviour plugins.

    Subclasses set :attr:`name`/:attr:`description` and override any subset of
    the hook methods below. Shared services are injected before
    :meth:`on_load` runs.
    """

    name: str = "Unnamed"
    description: str = ""
    emoji: str = "\N{ELECTRIC PLUG}"
    author: str = "unknown"
    version: str = "0.0.0"
    # Lower runs earlier in every hook chain.
    priority: int = 100
    # Declarative, db-backed options: {"key": default_value}. Overrides are
    # stored under db owner ``plugin.<name>``.
    options: dict[str, Any] = {}

    def __init__(self) -> None:
        self.app = None  # HarukaClient
        self.db = None  # Database
        self.core = None  # Application
        self.loader = None  # Loader

    # -- options ---------------------------------------------------------

    def option(self, key: str, default: Any = None) -> Any:
        """Read an option, honouring any db-stored override."""
        base = self.options.get(key, default)
        if self.db is None:
            return base
        stored = self.db.get(f"plugin.{self.name}", "options", {})
        return stored.get(key, base)

    async def set_option(self, key: str, value: Any) -> None:
        if self.db is None:
            return
        stored = dict(self.db.get(f"plugin.{self.name}", "options", {}))
        stored[key] = value
        await self.db.set(f"plugin.{self.name}", "options", stored)

    # -- lifecycle -------------------------------------------------------

    async def on_load(self) -> None:  # noqa: B027 - optional hook
        """Called once after the plugin is registered."""

    async def on_unload(self) -> None:  # noqa: B027 - optional hook
        """Called before the plugin is removed."""

    # -- behaviour hooks (all optional) ----------------------------------

    async def before_command(self, ctx: "Context") -> Optional[bool]:  # noqa: B027
        """Run before a command handler. Return ``False`` to veto it."""
        return None

    async def after_command(self, ctx: "Context") -> None:  # noqa: B027
        """Run after a command handler completes successfully."""

    async def transform_outgoing(self, text: str, ctx: "Context" = None) -> str:
        """Transform outgoing reply text. Return the (possibly) new text."""
        return text

    async def on_incoming(self, message: Any) -> None:  # noqa: B027
        """Observe every incoming message before command routing."""

    async def on_error(self, ctx: "Context", exc: BaseException) -> None:  # noqa: B027
        """React to a command failure."""


class LoadedPlugin:
    def __init__(self, instance: Plugin, origin: str, source_path: Optional[Path], import_name: str = ""):
        self.instance = instance
        self.origin = origin
        self.source_path = source_path
        self.import_name = import_name


class PluginError(Exception):
    """Raised when a plugin cannot be loaded."""


class PluginManager:
    """Owns the set of plugins and fans engine events out to their hooks."""

    def __init__(self, core: Any, db: Any):
        self.core = core
        self.db = db
        self.plugins: dict[str, LoadedPlugin] = {}

    # -- state -----------------------------------------------------------

    def _disabled(self) -> set[str]:
        return {name.casefold() for name in self.db.get("core", "disabled_plugins", [])}

    def is_enabled(self, name: str) -> bool:
        return name.casefold() not in self._disabled()

    async def set_enabled(self, name: str, enabled: bool) -> bool:
        loaded = self._find(name)
        if loaded is None:
            return False
        disabled = {item.casefold(): item for item in self.db.get("core", "disabled_plugins", [])}
        key = loaded.instance.name.casefold()
        if enabled:
            disabled.pop(key, None)
        else:
            disabled[key] = loaded.instance.name
        await self.db.set("core", "disabled_plugins", sorted(disabled.values(), key=str.casefold))
        return True

    def _find(self, name: str) -> Optional[LoadedPlugin]:
        want = name.casefold()
        for loaded in self.plugins.values():
            if loaded.instance.name.casefold() == want:
                return loaded
        return None

    def _active(self) -> list[LoadedPlugin]:
        disabled = self._disabled()
        active = [
            loaded
            for loaded in self.plugins.values()
            if loaded.instance.name.casefold() not in disabled
        ]
        active.sort(key=lambda item: item.instance.priority)
        return active

    # -- injection / registration ---------------------------------------

    def _inject(self, plugin: Plugin) -> None:
        plugin.core = self.core
        plugin.db = self.db
        plugin.loader = getattr(self.core, "loader", None)
        plugin.app = getattr(self.core, "client", None)

    async def _register(self, instance: Plugin, origin: str, source_path: Optional[Path], import_name: str = "") -> None:
        self._inject(instance)
        existing = self._find(instance.name)
        if existing is not None:
            if existing.origin == "builtin" and origin != "builtin":
                raise PluginError(f"Plugin name collision with a built-in: {instance.name}")
            await self.unload(instance.name)
        loaded = LoadedPlugin(instance, origin, source_path, import_name)
        self.plugins[instance.name] = loaded
        try:
            await instance.on_load()
        except Exception:
            self.plugins.pop(instance.name, None)
            raise
        logger.info("Loaded plugin '%s' (priority %d)", instance.name, instance.priority)

    @staticmethod
    def _instantiate(py_module) -> list[Plugin]:
        found: list[Plugin] = []
        for _, obj in inspect.getmembers(py_module, inspect.isclass):
            if (
                issubclass(obj, Plugin)
                and obj is not Plugin
                and obj.__module__ == py_module.__name__
            ):
                found.append(obj())
        return found

    # -- loading ---------------------------------------------------------

    async def load_builtins(self) -> None:
        try:
            package = importlib.import_module(_BUILTIN_PACKAGE)
        except ModuleNotFoundError:
            return
        for info in pkgutil.iter_modules(package.__path__):
            if info.name.startswith("_"):
                continue
            mod = importlib.import_module(f"{_BUILTIN_PACKAGE}.{info.name}")
            for instance in self._instantiate(mod):
                try:
                    await self._register(instance, "builtin", None, mod.__name__)
                except Exception:
                    logger.exception("Failed to load built-in plugin %s", info.name)

    async def load_user_plugins(self, plugins_dir: Path) -> None:
        plugins_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(plugins_dir.glob("*.py")):
            try:
                await self.load_from_path(path)
            except Exception:
                logger.exception("Failed to load user plugin %s", path.name)

    async def load_from_path(self, path: Path) -> list[str]:
        path = path.resolve()
        if path.suffix.lower() != ".py":
            raise PluginError("Only .py plugins are supported")
        import_key = re.sub(r"[^a-zA-Z0-9_]", "_", path.stem)
        import_name = f"haruka_plugin_{import_key}"
        spec = importlib.util.spec_from_file_location(import_name, path)
        if spec is None or spec.loader is None:
            raise PluginError(f"Cannot import {path}")
        py_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = py_module
        try:
            spec.loader.exec_module(py_module)
        except Exception:
            sys.modules.pop(spec.name, None)
            raise
        instances = self._instantiate(py_module)
        if not instances:
            sys.modules.pop(spec.name, None)
            raise PluginError(f"No Plugin subclass found in {path.name}")
        names = []
        for instance in instances:
            await self._register(instance, "user", path, spec.name)
            names.append(instance.name)
        return names

    async def install_from_source(self, code: str, filename: str, plugins_dir: Path) -> list[str]:
        plugins_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
        if not safe.endswith(".py"):
            safe += ".py"
        target = plugins_dir / safe
        target.write_text(code, encoding="utf-8")
        try:
            return await self.load_from_path(target)
        except Exception:
            target.unlink(missing_ok=True)
            raise

    async def unload(self, name: str) -> bool:
        loaded = self._find(name)
        if loaded is None:
            return False
        try:
            await loaded.instance.on_unload()
        except Exception:
            logger.exception("on_unload failed for plugin %s", name)
        self.plugins.pop(loaded.instance.name, None)
        if loaded.import_name and loaded.origin == "user":
            sys.modules.pop(loaded.import_name, None)
        return True

    async def reload(self, name: str) -> bool:
        loaded = self._find(name)
        if loaded is None or loaded.source_path is None:
            return False
        path = loaded.source_path
        await self.unload(name)
        await self.load_from_path(path)
        return True

    async def shutdown(self) -> None:
        for loaded in list(self.plugins.values()):
            try:
                await loaded.instance.on_unload()
            except Exception:
                logger.debug("on_unload failed during shutdown", exc_info=True)
        self.plugins.clear()

    # -- hook dispatch ---------------------------------------------------

    async def run_before_command(self, ctx: "Context") -> bool:
        """Return ``False`` if any plugin vetoes the command."""
        for loaded in self._active():
            try:
                result = await loaded.instance.before_command(ctx)
                if result is False:
                    logger.info("Command vetoed by plugin '%s'", loaded.instance.name)
                    return False
            except Exception:
                logger.exception("before_command failed in plugin %s", loaded.instance.name)
        return True

    async def run_after_command(self, ctx: "Context") -> None:
        for loaded in self._active():
            try:
                await loaded.instance.after_command(ctx)
            except Exception:
                logger.exception("after_command failed in plugin %s", loaded.instance.name)

    async def apply_outgoing(self, text: str, ctx: "Context" = None) -> str:
        for loaded in self._active():
            try:
                new_text = await loaded.instance.transform_outgoing(text, ctx)
                if isinstance(new_text, str):
                    text = new_text
            except Exception:
                logger.exception("transform_outgoing failed in plugin %s", loaded.instance.name)
        return text

    async def run_incoming(self, message: Any) -> None:
        for loaded in self._active():
            try:
                await loaded.instance.on_incoming(message)
            except Exception:
                logger.exception("on_incoming failed in plugin %s", loaded.instance.name)

    async def run_error(self, ctx: "Context", exc: BaseException) -> None:
        for loaded in self._active():
            try:
                await loaded.instance.on_error(ctx, exc)
            except Exception:
                logger.exception("on_error failed in plugin %s", loaded.instance.name)
