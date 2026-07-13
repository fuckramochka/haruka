"""Best-effort compatibility with the legacy Hikka/Heroku module API.

This is intentionally a thin shim, not a full re-implementation. It covers the
common surface (``loader.Module``, ``@loader.command``, ``utils.answer``,
string dicts) so that many simple community modules load unchanged. Modules
that reach deep into Hikka internals will not work — those should be ported to
the native :class:`haruka.api.Module` API.
"""

from haruka.compat.hikka import adapt_hikka_module, install_hikka_runtime

__all__ = ["adapt_hikka_module", "install_hikka_runtime"]
