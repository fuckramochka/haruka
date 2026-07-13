"""Public module-author API — the only import a module needs.

::

    from haruka.api import Module, command, watcher, Context, Role
"""

from haruka.core.config import ConfigOption, ModuleConfig
from haruka.core.context import Context
from haruka.core.metadata import ModuleManifest
from haruka.core.module import Module, callback, command, watcher
from haruka.core.plugins import Plugin
from haruka.core.security import Role
from haruka.ui import render
from haruka.ui.theme import get_theme
from haruka import utils
from haruka.i18n import MEME_LANGUAGES, SUPPORTED_LANGUAGES, Translator

__all__ = [
    "ConfigOption",
    "Context",
    "Module",
    "ModuleConfig",
    "Plugin",
    "ModuleManifest",
    "Role",
    "callback",
    "command",
    "get_theme",
    "render",
    "watcher",
    "utils",
    "Translator",
    "SUPPORTED_LANGUAGES",
    "MEME_LANGUAGES",
]
