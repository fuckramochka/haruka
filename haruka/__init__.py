"""Haruka — a clean, modern Telegram userbot built on Kurigram.

This package is a full rewrite (2.0). The public surface that modules are
expected to use lives in :mod:`haruka.api`.
"""

# Register the harukatl -> herokutl import alias as early as possible so that
# legacy modules (haruka.modules.*, user plugins) can simply ``import harukatl``.
# A failure here must never break ``import haruka`` itself.
try:
    from haruka import _harukatl

    _harukatl.install()
except Exception:  # pragma: no cover - defensive
    pass

from haruka.version import __version__, version_string

__all__ = ["__version__", "version_string"]
