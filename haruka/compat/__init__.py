"""Best-effort compatibility with the legacy Hikka/Heroku module API.

This is intentionally a thin shim, not a full re-implementation. It covers the
common surface (``loader.Module``, ``@loader.command``, ``utils.answer``,
string dicts) so that many simple community modules load unchanged. Modules
that reach deep into Hikka internals will not work — those should be ported to
the native :class:`haruka.api.Module` API.

The adapter (``haruka.compat.hikka``) imports the Telegram client stack, so it
is loaded lazily here: pulling in ``install_hikka_runtime`` / the synthetic
package machinery must not require pyrogram to be installed.
"""
from __future__ import annotations

from typing import Any

__all__ = ["adapt_hikka_module", "install_hikka_runtime"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from haruka.compat import hikka

        return getattr(hikka, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
