"""Compatibility import hook: harukatl -> herokutl.

Haruka is a fork of Heroku. All Haruka code (core + modules/plugins) imports
`harukatl`, but the actual Telegram library shipped on PyPI is `herokutl`
(package `heroku-tl-new`). Instead of vendoring or renaming the dependency, we
intercept every `harukatl[.*]` import and transparently redirect it to the real
`herokutl[.*]` module. This keeps the branding "Haruka" everywhere in source
while reusing the upstream library unchanged.

Works for both static imports in the core and dynamic plugin imports, because a
MetaPathFinder is consulted by every import going through the standard import
system (including loader.patched_import -> native_import).
"""

# ©️ Codrago, 2024-2030
# This file is a part of Haruka Userbot
# 🌐 https://github.com/coddrago/Heroku
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import importlib
import importlib.abc
import importlib.machinery
import sys

_ALIAS = "harukatl"
_REAL = "herokutl"


class _AliasLoader(importlib.abc.Loader):
    """Loads harukatl[.sub] by importing the matching herokutl[.sub]."""

    def create_module(self, spec):
        real_name = _REAL + spec.name[len(_ALIAS):]
        module = importlib.import_module(real_name)
        # Alias both directions so `is` checks and repeated imports stay stable.
        sys.modules[spec.name] = module
        return module

    def exec_module(self, module):  # already executed as herokutl
        pass


class HarukaTlFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == _ALIAS or fullname.startswith(_ALIAS + "."):
            return importlib.machinery.ModuleSpec(fullname, _AliasLoader())
        return None


def install() -> None:
    """Register the harukatl -> herokutl redirect exactly once."""
    if any(isinstance(finder, HarukaTlFinder) for finder in sys.meta_path):
        return
    sys.meta_path.insert(0, HarukaTlFinder())
