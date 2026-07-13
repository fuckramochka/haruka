"""Public module-author API — the only import a module needs.

::

    from haruka.api import Module, command, watcher, Context, Role
"""

from haruka.core.config import ConfigOption, ModuleConfig
from haruka.core.context import Context
from haruka.core.module import Module, callback, command, watcher
from haruka.core.security import Role
from haruka.ui import render
from haruka.ui.theme import get_theme
from haruka import utils
from haruka.i18n import Translator

__all__ = [
    "ConfigOption",
    "Context",
    "Module",
    "ModuleConfig",
    "Role",
    "callback",
    "command",
    "get_theme",
    "render",
    "watcher",
    "utils",
    "Translator",
]
