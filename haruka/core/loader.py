"""Module loader.

Discovers, imports, and registers modules — both built-ins (shipped in
``haruka.modules``) and user modules (single ``.py`` files dropped into the
data ``modules/`` directory or installed from a URL / reply). Handles service
injection, config binding, command indexing and hot-reload.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import pkgutil
import re
import hashlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from haruka.core.metadata import (
    ModuleManifest,
    engine_satisfies,
    install_requirements,
    missing_requirements,
    parse_manifest,
    screen_requirements,
)
from haruka.core.module import (
    BoundCallback,
    BoundCommand,
    BoundWatcher,
    Module,
)
from haruka.version import __version__ as ENGINE_VERSION

if TYPE_CHECKING:
    from haruka.core.client import HarukaClient
    from haruka.core.config import Settings
    from haruka.core.database import Database
    from haruka.inline.bot import InlineBot

logger = logging.getLogger(__name__)

_BUILTIN_PACKAGE = "haruka.modules"


class ModuleLoadError(RuntimeError):
    """A module could not be loaded without corrupting runtime state."""


class LoadedModule:
    def __init__(self, instance: Module, origin: str, source_path: Optional[Path], import_name: str = "", manifest: Optional[ModuleManifest] = None):
        self.instance = instance
        self.origin = origin  # "builtin" | "user"
        self.source_path = source_path
        self.import_name = import_name
        self.manifest = manifest or ModuleManifest()
        self.commands: list[BoundCommand] = []
        self.watchers: list[BoundWatcher] = []
        self.callbacks: list[BoundCallback] = []


class Loader:
    def __init__(
        self,
        client: "HarukaClient",
        db: "Database",
        settings: "Settings",
    ):
        self.client = client
        self.db = db
        self.settings = settings
        self.bot: Optional["InlineBot"] = None
        # Set by Application after construction; lets modules reach app-level
        # services (security, uptime, restart) without global state.
        self.app_ref = None

        self.modules: dict[str, LoadedModule] = {}
        self._commands: dict[str, BoundCommand] = {}
        self.watchers: list[BoundWatcher] = []
        self.callbacks: list[BoundCallback] = []

    # -- lookups ---------------------------------------------------------

    def find_command(self, name: str) -> Optional[BoundCommand]:
        return self._commands.get(name.lower())

    def resolve_module_name(self, name: str) -> Optional[str]:
        wanted = name.casefold()
        return next((key for key in self.modules if key.casefold() == wanted), None)

    def is_command_enabled(self, name: str) -> bool:
        return name.lower() not in set(self.db.get("core", "disabled_commands", []))

    def is_module_enabled(self, name: str) -> bool:
        disabled = {item.casefold() for item in self.db.get("core", "disabled_modules", [])}
        return name.casefold() not in disabled

    async def set_command_enabled(self, name: str, enabled: bool) -> None:
        key = name.lower()
        values = set(self.db.get("core", "disabled_commands", []))
        values.discard(key) if enabled else values.add(key)
        await self.db.set("core", "disabled_commands", sorted(values))

    async def set_module_enabled(self, name: str, enabled: bool) -> None:
        canonical = self.resolve_module_name(name) or name
        values = {item.casefold(): item for item in self.db.get("core", "disabled_modules", [])}
        values.pop(canonical.casefold(), None) if enabled else values.__setitem__(canonical.casefold(), canonical)
        await self.db.set("core", "disabled_modules", sorted(values.values(), key=str.casefold))

    @property
    def command_names(self) -> list[str]:
        return sorted(self._commands)

    def module_names(self) -> list[str]:
        return sorted(self.modules)

    def find_callback(self, data: str) -> Optional[BoundCallback]:
        for cb in self.callbacks:
            if cb.spec.prefix and data.startswith(cb.spec.prefix):
                return cb
        return None

    # -- registration ----------------------------------------------------

    def _inject(self, module: Module) -> None:
        module.app = self.client
        module.db = self.db
        module.bot = self.bot
        module.loader = self
        from haruka import ui  # local import to avoid cycles

        module.ui = ui

    async def _register(
        self, instance: Module, origin: str, source_path: Optional[Path], import_name: str = "", manifest: Optional[ModuleManifest] = None
    ) -> LoadedModule:
        self._inject(instance)

        # Register per-module localization strings, if any were declared.
        translator = getattr(self.app_ref, "translator", None)
        if translator is not None and getattr(instance, "strings", None):
            try:
                translator.register_module_strings(instance.name, instance.strings)
            except Exception:
                logger.debug("Could not register strings for %s", instance.name, exc_info=True)

        # Bind declarative config to the database if the module declared one.
        if instance.config is not None:
            owner = f"config.{instance.name}"
            stored = self.db.get(owner, "values", {})

            async def _persist(key: str, value, _owner=owner):
                values = dict(self.db.get(_owner, "values", {}))
                values[key] = value
                await self.db.set(_owner, "values", values)

            instance.config.bind(stored, _persist)

        existing_name = self.resolve_module_name(instance.name)
        existing = self.modules.get(existing_name) if existing_name else None
        if existing is not None and (existing.origin == "builtin" or origin == "builtin"):
            raise ModuleLoadError(f"Module name collision: {instance.name}")

        loaded = LoadedModule(instance, origin, source_path, import_name, manifest)
        loaded.commands = instance.collect_commands()
        loaded.watchers = instance.collect_watchers()
        loaded.callbacks = instance.collect_callbacks()

        # Refuse ambiguous routing. Replacements may reuse only their own routes.
        for cmd in loaded.commands:
            for name in [cmd.name, *cmd.spec.aliases]:
                key = name.lower()
                owner = self._commands.get(key)
                if owner and (existing is None or owner.module is not existing.instance):
                    raise ModuleLoadError(
                        f"Command collision: '{key}' already belongs to {owner.module.name}"
                    )

        snapshot = (
            dict(self.modules), dict(self._commands), list(self.watchers), list(self.callbacks)
        )
        if existing_name:
            self.modules.pop(existing_name, None)
            self._rebuild_indexes()
        self.modules[instance.name] = loaded
        for cmd in loaded.commands:
            self._commands[cmd.name] = cmd
            for alias in cmd.spec.aliases:
                self._commands[alias.lower()] = cmd
        self.watchers.extend(loaded.watchers)
        self.callbacks.extend(loaded.callbacks)

        try:
            await instance.on_load()
        except Exception:
            self.modules, self._commands, self.watchers, self.callbacks = snapshot
            if import_name:
                sys.modules.pop(import_name, None)
            raise
        if existing is not None:
            try:
                await existing.instance.on_unload()
            except Exception:
                logger.exception("on_unload failed for replaced module %s", existing_name)
        logger.info(
            "Loaded module '%s' (%d cmd, %d watch)",
            instance.name,
            len(loaded.commands),
            len(loaded.watchers),
        )
        return loaded

    def _rebuild_indexes(self) -> None:
        self._commands.clear()
        self.watchers.clear()
        self.callbacks.clear()
        for loaded in self.modules.values():
            for cmd in loaded.commands:
                self._commands[cmd.name] = cmd
                for alias in cmd.spec.aliases:
                    self._commands[alias.lower()] = cmd
            self.watchers.extend(loaded.watchers)
            self.callbacks.extend(loaded.callbacks)

    # -- built-in loading ------------------------------------------------

    async def load_builtins(self) -> None:
        package = importlib.import_module(_BUILTIN_PACKAGE)
        for info in pkgutil.iter_modules(package.__path__):
            if info.name.startswith("_"):
                continue
            mod = importlib.import_module(f"{_BUILTIN_PACKAGE}.{info.name}")
            for instance in self._instantiate_modules(mod):
                await self._register(instance, "builtin", None, mod.__name__)

    async def load_user_modules(self) -> None:
        modules_dir = self.settings.modules_dir
        modules_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(modules_dir.glob("*.py")):
            try:
                await self.load_from_path(path)
            except Exception:
                logger.exception("Failed to load user module %s", path.name)

    # -- dynamic loading -------------------------------------------------

    @staticmethod
    def _instantiate_modules(py_module) -> list[Module]:
        found: list[Module] = []
        for _, obj in inspect.getmembers(py_module, inspect.isclass):
            if (
                issubclass(obj, Module)
                and obj is not Module
                and obj.__module__ == py_module.__name__
            ):
                found.append(obj())
        return found

    async def load_from_path(self, path: Path) -> list[str]:
        # Make the Hikka shim importable before executing user code, so legacy
        # ``import loader, utils`` statements resolve during import.
        from haruka.compat.hikka_runtime import install_hikka_runtime

        install_hikka_runtime()

        path = path.resolve()
        if path.suffix.lower() != ".py":
            raise ModuleLoadError("Only .py modules are supported")

        # Parse the declarative manifest and provision it before executing any
        # third-party code. Failing fast here keeps a half-satisfied import out
        # of the runtime.
        manifest = parse_manifest(path.read_text(encoding="utf-8"))
        if not engine_satisfies(manifest.min_engine, ENGINE_VERSION):
            raise ModuleLoadError(
                f"Module requires engine >= {manifest.min_engine} (running {ENGINE_VERSION})"
            )
        if manifest.requires:
            # Supply-chain screening: never hand a suspicious dependency to pip.
            blocked, warnings = screen_requirements(manifest.requires)
            if blocked:
                raise ModuleLoadError(
                    "Refusing to install suspicious dependencies (possible "
                    "supply-chain attack): " + ", ".join(blocked)
                )
            for name in warnings:
                logger.warning("Module %s requests unpinned dependency '%s'", path.name, name)
            # Installing third-party code is opt-in. The owner enables it once
            # with '.installs on' after reviewing the module source.
            needed = missing_requirements(manifest.requires)
            if needed and not bool(self.db.get("core", "allow_untrusted_installs", False)):
                raise ModuleLoadError(
                    "This module wants to install: " + ", ".join(needed) + ". "
                    "Review the source, then run '.installs on' to allow it."
                )
            ok, attempted = install_requirements(manifest.requires)
            if not ok:
                raise ModuleLoadError(
                    "Could not install dependencies: " + ", ".join(attempted)
                )
        self._pending_manifest = manifest
        import_key = re.sub(r"[^a-zA-Z0-9_]", "_", path.stem)
        digest = hashlib.sha1(str(path).encode(), usedforsecurity=False).hexdigest()[:10]
        # Execute the module *inside* the compatibility package so that legacy
        # relative imports (``from .. import loader, utils``) resolve instead of
        # raising "attempted relative import with no known parent package".
        from haruka.compat.hikka_runtime import USER_MODULE_PACKAGE

        import_name = f"{USER_MODULE_PACKAGE}.{import_key}_{digest}"
        spec = importlib.util.spec_from_file_location(import_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot import {path}")
        py_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = py_module
        try:
            spec.loader.exec_module(py_module)
        except Exception:
            sys.modules.pop(spec.name, None)
            raise

        # Try native modules first, then Hikka compatibility shim.
        instances = self._instantiate_modules(py_module)
        if not instances:
            from haruka.compat.hikka import adapt_hikka_module

            adapted = adapt_hikka_module(py_module)
            if adapted is not None:
                instances = [adapted]

        if not instances:
            sys.modules.pop(spec.name, None)
            raise ImportError(f"No Haruka module found in {path.name}")

        names = []
        try:
            for instance in instances:
                instance.manifest = manifest
                await self._register(instance, "user", path, spec.name, manifest)
                names.append(instance.name)
        except Exception:
            for name in reversed(names):
                await self.unload(name)
            raise
        return names

    async def install_from_source(self, code: str, filename: str) -> list[str]:
        modules_dir = self.settings.modules_dir
        modules_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(filename).name
        if not filename.lower().endswith(".py"):
            filename += ".py"
        if filename.startswith("."):
            raise ModuleLoadError("Invalid module filename")
        target = modules_dir / filename
        previous = target.read_bytes() if target.exists() else None
        temporary = target.with_suffix(target.suffix + ".new")
        temporary.write_text(code, encoding="utf-8")
        temporary.replace(target)
        try:
            return await self.load_from_path(target)
        except Exception:
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(previous)
            raise

    # -- unload / reload -------------------------------------------------

    async def unload(self, name: str) -> bool:
        canonical = self.resolve_module_name(name)
        loaded = self.modules.get(canonical) if canonical else None
        if loaded is None:
            return False
        if loaded.origin == "builtin":
            raise ValueError("Cannot unload a built-in module")
        try:
            await loaded.instance.on_unload()
        except Exception:
            logger.exception("on_unload failed for %s", name)
        del self.modules[canonical]
        self._rebuild_indexes()
        import_in_use = any(
            item.import_name == loaded.import_name for item in self.modules.values()
        )
        if loaded.import_name and loaded.origin == "user" and not import_in_use:
            sys.modules.pop(loaded.import_name, None)
        logger.info("Unloaded module '%s'", canonical)
        return True

    async def reload(self, name: str) -> bool:
        canonical = self.resolve_module_name(name)
        loaded = self.modules.get(canonical) if canonical else None
        if loaded is None or loaded.source_path is None:
            return False
        path = loaded.source_path
        await self.load_from_path(path)
        return True

    def source_of(self, name: str) -> Optional[Path]:
        canonical = self.resolve_module_name(name)
        loaded = self.modules.get(canonical) if canonical else None
        return loaded.source_path if loaded else None

    async def shutdown(self) -> None:
        """Run unload hooks for every module during graceful shutdown."""
        for loaded in reversed(list(self.modules.values())):
            try:
                await loaded.instance.on_unload()
            except Exception:
                logger.exception("on_unload failed for %s", loaded.instance.name)
