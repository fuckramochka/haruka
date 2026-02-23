"""Compatibility alias package for TL backend."""

import importlib as _importlib
import pkgutil as _pkgutil
import sys as _sys

_base = None
_base_name = ""
_alias_base = __name__

for _candidate in ("telethon", "he" + "roku" + "tl"):
    try:
        _base = _importlib.import_module(_candidate)
        _base_name = _candidate
        break
    except Exception:
        continue

if _base is None:
    raise ModuleNotFoundError("Neither Telethon nor compatible TL backend is installed")

globals().update(_base.__dict__)

__all__ = getattr(_base, "__all__", [])
__path__ = getattr(_base, "__path__", [])
__file__ = getattr(_base, "__file__", None)
__name__ = _alias_base
__package__ = _alias_base

for _name, _module in list(_sys.modules.items()):
    if _name == _base_name or _name.startswith(_base_name + "."):
        _alias = _alias_base + _name[len(_base_name) :]
        _sys.modules.setdefault(_alias, _module)

# Keep the most commonly type-checked submodules mapped 1:1 to base backend.
# Without this, imports like `harukatl.sessions` may be loaded as separate
# module objects and break `isinstance` checks in backend internals.
for _submodule in (
    "sessions",
    "sessions.abstract",
    "sessions.memory",
    "sessions.sqlite",
    "sessions.string",
    "errors",
    "errors.common",
    "errors.rpcbaseerrors",
    "errors.rpcerrorlist",
):
    try:
        _real_name = f"{_base_name}.{_submodule}"
        _real_module = _importlib.import_module(_real_name)
        _sys.modules[f"{_alias_base}.{_submodule}"] = _real_module
    except Exception:
        continue

# Preload and alias direct children to minimize accidental duplicate imports.
for _module_info in _pkgutil.iter_modules(getattr(_base, "__path__", [])):
    _child = _module_info.name
    _real_name = f"{_base_name}.{_child}"
    try:
        _real_module = _importlib.import_module(_real_name)
    except Exception:
        continue

    _sys.modules.setdefault(f"{_alias_base}.{_child}", _real_module)
