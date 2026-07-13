"""The module authoring API.

A module is a subclass of :class:`Module`. Command / watcher / callback
handlers are declared with decorators, discovered at load time, and given a
rich :class:`Context` at call time. This is the "clean new API" — no globals,
no monkeypatching, no magic reference finding.

Example::

    from haruka.api import Module, command, Context

    class Hello(Module):
        name = "Hello"
        description = "Greets people"

        @command(aliases=["hi"], doc="Say hello")
        async def hello(self, ctx: Context):
            await ctx.ok(f"Hello, {ctx.sender_name}!")
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

from haruka.core.security import Role

if TYPE_CHECKING:
    from haruka.core.context import Context


# -- decorators --------------------------------------------------------------

_COMMAND_ATTR = "__haruka_command__"
_WATCHER_ATTR = "__haruka_watcher__"
_CALLBACK_ATTR = "__haruka_callback__"


@dataclass
class CommandSpec:
    name: Optional[str] = None
    aliases: list[str] = field(default_factory=list)
    role: Role = Role.OWNER
    doc: str = ""
    usage: str = ""
    hidden: bool = False


@dataclass
class WatcherSpec:
    incoming: bool = True
    outgoing: bool = False
    only_groups: bool = False
    only_private: bool = False
    only_reply: bool = False
    only_forward: bool = False
    only_mention: bool = False
    no_bots: bool = False
    no_commands: bool = False


@dataclass
class CallbackSpec:
    prefix: str = ""


def command(
    name: Optional[str] = None,
    *,
    aliases: Optional[list[str]] = None,
    role: Role = Role.OWNER,
    doc: str = "",
    usage: str = "",
    hidden: bool = False,
) -> Callable:
    """Mark a method as a chat command."""

    def decorator(func: Callable) -> Callable:
        setattr(
            func,
            _COMMAND_ATTR,
            CommandSpec(
                name=name,
                aliases=aliases or [],
                role=role,
                doc=doc or (func.__doc__ or "").strip(),
                usage=usage,
                hidden=hidden,
            ),
        )
        return func

    return decorator


def watcher(
    *,
    incoming: bool = True,
    outgoing: bool = False,
    only_groups: bool = False,
    only_private: bool = False,
    only_reply: bool = False,
    only_forward: bool = False,
    only_mention: bool = False,
    no_bots: bool = False,
    no_commands: bool = False,
) -> Callable:
    """Mark a method as a passive message watcher."""

    def decorator(func: Callable) -> Callable:
        setattr(
            func,
            _WATCHER_ATTR,
            WatcherSpec(
                incoming=incoming,
                outgoing=outgoing,
                only_groups=only_groups,
                only_private=only_private,
                only_reply=only_reply,
                only_forward=only_forward,
                only_mention=only_mention,
                no_bots=no_bots,
                no_commands=no_commands,
            ),
        )
        return func

    return decorator


def callback(prefix: str = "") -> Callable:
    """Mark a method as an inline callback handler (Control Center wiring)."""

    def decorator(func: Callable) -> Callable:
        setattr(func, _CALLBACK_ATTR, CallbackSpec(prefix=prefix))
        return func

    return decorator


# -- bound handler records ----------------------------------------------------


@dataclass
class BoundCommand:
    name: str
    spec: CommandSpec
    handler: Callable[["Context"], Any]
    module: "Module"


@dataclass
class BoundWatcher:
    spec: WatcherSpec
    handler: Callable[["Context"], Any]
    module: "Module"


@dataclass
class BoundCallback:
    spec: CallbackSpec
    handler: Callable
    module: "Module"


# -- base module --------------------------------------------------------------


class Module:
    """Base class for all Haruka modules.

    Subclasses set :attr:`name` and :attr:`description`, then declare handlers
    with the decorators above. The loader injects shared services before
    :meth:`on_load` is awaited.
    """

    name: str = "Unnamed"
    description: str = ""
    # Emoji shown next to the module in help / control center.
    emoji: str = "\N{JIGSAW PUZZLE PIECE}"
    author: str = "unknown"
    version: str = "0.0.0"
    requires: tuple[str, ...] = ()
    # Optional per-module localization: {"key": "English"} or
    # {"key": {"en": "...", "ru": "..."}}. Registered at load time.
    strings: dict = {}

    def __init__(self) -> None:
        # Injected by the loader.
        self.app = None  # HarukaClient
        # Declarative manifest parsed from the source header (see
        # haruka.core.metadata). Empty for built-ins unless they set it.
        self.manifest = None
        self.db = None  # Database
        self.bot = None  # InlineBot | None
        self.ui = None  # ui theme/render facade
        self.loader = None  # Loader
        self.config = None  # ModuleConfig | None (module may set its own)

    # Overridable lifecycle hooks.
    async def on_load(self) -> None:  # noqa: B027 - intentional no-op hook
        """Called once after the module is registered and services injected."""

    async def on_unload(self) -> None:  # noqa: B027 - intentional no-op hook
        """Called before the module is removed (cleanup timers, etc.)."""

    # Discovery helpers used by the loader.
    def collect_commands(self) -> list[BoundCommand]:
        found: list[BoundCommand] = []
        for _, member in inspect.getmembers(self, predicate=callable):
            spec: Optional[CommandSpec] = getattr(member, _COMMAND_ATTR, None)
            if spec is None:
                continue
            cmd_name = (spec.name or member.__name__).lower().lstrip("_")
            found.append(BoundCommand(cmd_name, spec, member, self))
        return found

    def collect_watchers(self) -> list[BoundWatcher]:
        found: list[BoundWatcher] = []
        for _, member in inspect.getmembers(self, predicate=callable):
            spec: Optional[WatcherSpec] = getattr(member, _WATCHER_ATTR, None)
            if spec is not None:
                found.append(BoundWatcher(spec, member, self))
        return found

    def collect_callbacks(self) -> list[BoundCallback]:
        found: list[BoundCallback] = []
        for _, member in inspect.getmembers(self, predicate=callable):
            spec: Optional[CallbackSpec] = getattr(member, _CALLBACK_ATTR, None)
            if spec is not None:
                found.append(BoundCallback(spec, member, self))
        return found
