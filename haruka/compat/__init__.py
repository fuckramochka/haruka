# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""
Universal compatibility layer of Haruka.

Haruka runs modules written for **any** major userbot fork without
modifications:

- **Hikka**: `import hikka...` → `haruka...`, `hikkatl` → `telethon`,
  `client.hikka_*` attributes, `hikka.*` database keys;
- **Heroku**: `import heroku...` → `haruka...`, `herokutl` → `telethon`,
  `client.heroku_*` attributes, `heroku.*` database keys;
- **FTG/GeekTG**: relative inline imports are rewritten on load
  (see :mod:`haruka.compat.geek`), plain Telethon API underneath.

Two mechanisms work together:

1. A meta-path finder (:func:`install_imports`) which transparently
   resolves legacy package names to their modern equivalents and
   registers them in ``sys.modules``, so both ``import hikka.loader``
   and ``importlib.import_module("hikka.loader")`` return the very
   same object as ``haruka.loader``.
2. Attribute sync helper (:func:`sync_client_attributes`) keeping
   legacy client shortcuts (``client.hikka_db``, ``client.heroku_inline``)
   pointing at live objects.
"""

import importlib
import importlib.machinery
import importlib.util
import logging
import sys

try:
    from importlib.abc import Loader
except ImportError:  # pragma: no cover
    Loader = object

logger = logging.getLogger(__name__)

# Legacy top-level package name → modern top-level package name
ALIASED_ROOTS = {
    "hikka": "haruka",
    "heroku": "haruka",
    "ftg": "haruka",
    "geektg": "haruka",
    "hikkatl": "telethon",
    "herokutl": "telethon",
}

_LEGACY_ATTR_PREFIXES = ("hikka", "heroku")

_INSTALLED = False


class AliasLoader(Loader):
    """Loader returning an already-imported real module for a legacy alias"""

    def __init__(self, real_name: str):
        self._real_name = real_name

    def create_module(self, spec):
        return importlib.import_module(self._real_name)

    def exec_module(self, module):
        """No-op: the real module is already fully executed"""

    def __repr__(self):
        return f"<AliasLoader {self._real_name!r}>"


class LegacyAliasFinder:
    """Meta-path finder resolving legacy fork imports to modern ones"""

    def find_spec(self, fullname: str, path=None, target=None):
        root, _, rest = fullname.partition(".")
        real_root = ALIASED_ROOTS.get(root)
        if not real_root:
            return None

        real_name = f"{real_root}.{rest}" if rest else real_root

        try:
            importlib.import_module(real_name)
        except Exception:
            logger.debug(
                "Legacy alias %s → %s: target unavailable", fullname, real_name
            )
            return None

        try:
            real_spec = importlib.util.find_spec(real_name)
        except Exception:
            real_spec = None

        spec = importlib.machinery.ModuleSpec(
            fullname,
            AliasLoader(real_name),
            is_package=bool(getattr(real_spec, "submodule_search_locations", None)),
        )

        if getattr(real_spec, "submodule_search_locations", None):
            spec.submodule_search_locations = list(
                real_spec.submodule_search_locations
            )

        logger.debug("Resolved legacy import %s → %s", fullname, real_name)
        return spec


def install_imports() -> None:
    """
    Register the meta-path finder mapping legacy userbot-fork packages
    (hikka, heroku, ftg, geektg, hikkatl, herokutl) onto Haruka/Telethon.
    Safe to call multiple times.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    if any(isinstance(finder, LegacyAliasFinder) for finder in sys.meta_path):
        _INSTALLED = True
        return

    sys.meta_path.insert(0, LegacyAliasFinder())
    _INSTALLED = True
    logger.debug("Legacy import aliases installed: %s", sorted(ALIASED_ROOTS))


def sync_client_attributes(client):
    """
    Mirror every ``client.haruka_*`` shortcut onto legacy ``hikka_*`` /
    ``heroku_*`` names, so modules written for Hikka or Heroku keep working.

    Handled attributes: me, db, inline, loader, allmodules, dispatcher —
    anything already present on the client under its ``haruka_*`` name.
    """
    if client is None:
        return client

    for attr in ("me", "db", "inline", "loader", "allmodules", "dispatcher"):
        value = getattr(client, f"haruka_{attr}", None)
        if value is None:
            continue

        for prefix in _LEGACY_ATTR_PREFIXES:
            try:
                setattr(client, f"{prefix}_{attr}", value)
            except AttributeError:
                pass

    return client


def install() -> None:
    """Install the whole compatibility layer"""
    install_imports()
