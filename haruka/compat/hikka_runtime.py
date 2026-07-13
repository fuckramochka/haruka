"""Fake ``loader`` / ``utils`` / ``translations`` modules.

Legacy Hikka modules do ``from .. import loader, utils`` at import time. We
register lightweight stand-ins in :data:`sys.modules` so those imports resolve
without pulling in the old framework. The stand-ins record just enough
metadata (command methods, config, strings) for :mod:`haruka.compat.hikka` to
build a native adapter.
"""

from __future__ import annotations

import logging
import sys
import types
from typing import Any, Callable

logger = logging.getLogger(__name__)

_INSTALLED = False

# User modules are executed *inside* this synthetic package so that the
# relative imports real Hikka/Heroku modules use at the top of the file
# (``from .. import loader, utils`` / ``from . import loader``) resolve to our
# shims instead of raising "attempted relative import with no known parent
# package". Aliases cover both community naming conventions.
USER_MODULE_PACKAGE = "heroku.modules"
_COMPAT_PACKAGE_ROOTS = ("heroku", "hikka")
_SHIM_NAMES = ("loader", "utils", "translations", "validators")


# -- loader.* ----------------------------------------------------------------


class _StringLoader:
    """Marks a class attribute as a translatable string dict (``strings``)."""


def _command(*args: Any, **kwargs: Any):
    """``@loader.command(...)`` — mark a coroutine as a command handler."""

    def decorator(func: Callable) -> Callable:
        func.__hikka_command__ = kwargs or {}
        return func

    # Support bare ``@loader.command`` usage too.
    if len(args) == 1 and callable(args[0]) and not kwargs:
        args[0].__hikka_command__ = {}
        return args[0]
    return decorator


def _watcher(*args: Any, **kwargs: Any):
    def decorator(func: Callable) -> Callable:
        func.__hikka_watcher__ = kwargs or {}
        return func

    if len(args) == 1 and callable(args[0]) and not kwargs:
        args[0].__hikka_watcher__ = {}
        return args[0]
    return decorator


def _tag(*tags: Any, **kwargs: Any):
    """No-op passthrough for ``@loader.tag`` style decorators."""

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def _identity_decorator(*args: Any, **kwargs: Any):
    """Preserve functions for legacy security/callback decorators."""
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    return lambda func: func


class _ConfigValue:
    def __init__(self, option: str = "", default: Any = None, doc: str = "", *a: Any, **k: Any):
        self.option = option
        self.default = default
        self.doc = doc


class _ModuleConfig(dict):
    """Behaves like Hikka's ``loader.ModuleConfig`` — an ordered mapping."""

    def __init__(self, *args: Any):
        super().__init__()
        self._defaults: dict[str, Any] = {}
        # Hikka passes triples/ConfigValue objects positionally.
        it = iter(args)
        for item in it:
            if isinstance(item, _ConfigValue):
                self[item.option] = item.default
                self._defaults[item.option] = item.default
            else:
                # (name, default, doc, ...) tuple style
                key = item
                default = next(it, None)
                # Skip the doc string if present.
                try:
                    next(it)
                except StopIteration:
                    pass
                self[key] = default
                self._defaults[key] = default

    def getdef(self, key: str) -> Any:
        return self._defaults.get(key)


def _build_loader_module() -> types.ModuleType:
    mod = types.ModuleType("loader")
    mod.Module = object  # replaced per-class check in adapter via duck typing
    mod.command = _command
    mod.watcher = _watcher
    mod.tag = _tag
    mod.loop = _tag
    mod.tds = _identity_decorator
    mod.owner = _identity_decorator
    mod.sudo = _identity_decorator
    mod.unrestricted = _identity_decorator
    mod.inline_everyone = _identity_decorator
    mod.callback_handler = _identity_decorator
    mod.raw_handler = _identity_decorator
    mod.ConfigValue = _ConfigValue
    mod.ModuleConfig = _ModuleConfig
    mod.StringLoader = _StringLoader
    # Hikka exposes a sentinel base class named ``Module``; community modules
    # subclass it. We use a real class so ``issubclass`` works.

    class HikkaModule:  # noqa: D401 - shim base
        strings = {"name": "Unknown"}

    mod.Module = HikkaModule
    return mod


# -- utils.* -----------------------------------------------------------------


async def _answer(message: Any, text: str, *args: Any, **kwargs: Any):
    """``utils.answer`` — edit own message or reply."""
    try:
        if getattr(message, "outgoing", False):
            return await message.edit_text(text)
        return await message.reply_text(text)
    except Exception:  # noqa: BLE001
        return await message.reply_text(text)


def _get_args_raw(message: Any) -> str:
    text = getattr(message, "text", "") or getattr(message, "caption", "") or ""
    parts = text.split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


def _get_args(message: Any) -> list[str]:
    raw = _get_args_raw(message)
    return raw.split() if raw else []


def _escape_html(text: Any) -> str:
    import html

    return html.escape(str(text))


def _build_utils_module() -> types.ModuleType:
    mod = types.ModuleType("utils")
    mod.answer = _answer
    mod.get_args_raw = _get_args_raw
    mod.get_args = _get_args
    mod.escape_html = _escape_html
    mod.get_chat_id = lambda m: getattr(getattr(m, "chat", None), "id", None)
    mod.get_display_name = lambda e: getattr(e, "first_name", None) or getattr(e, "title", "?")
    return mod


def _build_translations_module() -> types.ModuleType:
    mod = types.ModuleType("translations")

    class Strings(dict):
        def __call__(self, key: str, _fallback: str = "") -> str:
            return self.get(key, _fallback or key)

    mod.Strings = Strings
    return mod


def _build_validators_module() -> types.ModuleType:
    mod = types.ModuleType("validators")

    class Validator:
        def __init__(self, *args: Any, **kwargs: Any):
            self.args, self.kwargs = args, kwargs

        def __call__(self, value: Any) -> Any:
            return value

    for name in ("Boolean", "String", "Integer", "Float", "Choice", "MultiChoice", "Link", "RegExp", "TelegramID", "EntityLike", "Emoji"):
        setattr(mod, name, type(name, (Validator,), {}))
    mod.Validator = Validator
    return mod


def _build_shims() -> dict[str, types.ModuleType]:
    return {
        "loader": _build_loader_module(),
        "utils": _build_utils_module(),
        "translations": _build_translations_module(),
        "validators": _build_validators_module(),
    }


def _register_compat_packages(shims: dict[str, types.ModuleType]) -> None:
    """Create fake ``heroku``/``hikka`` packages hosting the shim submodules.

    Real community modules import their framework relatively, e.g.
    ``from .. import loader, utils``. Executing a user module under
    :data:`USER_MODULE_PACKAGE` (``heroku.modules.<name>``) means ``..`` is
    ``heroku`` and ``.`` is ``heroku.modules`` — so we expose the shims under
    both levels of both naming roots.
    """
    for root in _COMPAT_PACKAGE_ROOTS:
        root_pkg = sys.modules.get(root)
        if root_pkg is None:
            root_pkg = types.ModuleType(root)
            root_pkg.__path__ = []  # mark as a package
            sys.modules[root] = root_pkg
        modules_pkg_name = f"{root}.modules"
        modules_pkg = sys.modules.get(modules_pkg_name)
        if modules_pkg is None:
            modules_pkg = types.ModuleType(modules_pkg_name)
            modules_pkg.__path__ = []
            sys.modules[modules_pkg_name] = modules_pkg
            setattr(root_pkg, "modules", modules_pkg)
        for name in _SHIM_NAMES:
            shim = shims[name]
            # Expose at both ``root.name`` (for ``from ..``) and
            # ``root.modules.name`` (for ``from .``).
            sys.modules.setdefault(f"{root}.{name}", shim)
            sys.modules.setdefault(f"{modules_pkg_name}.{name}", shim)
            setattr(root_pkg, name, shim)
            setattr(modules_pkg, name, shim)


def install_hikka_runtime() -> None:
    """Register the shim modules once, before any user module is imported."""
    global _INSTALLED
    if _INSTALLED:
        return
    shims = _build_shims()
    for name, shim in shims.items():
        sys.modules.setdefault(name, shim)
    _register_compat_packages(shims)
    _INSTALLED = True
    logger.info("Hikka compatibility runtime installed")


def hikka_base_class():
    """Return the shim ``loader.Module`` base class."""
    install_hikka_runtime()
    return sys.modules["loader"].Module
