"""haruka.tl — the layer that compensates Kurigram's weak spots.

Kurigram's high-level API is clean but hides raw MTProto. This package gives
modules ergonomic access to raw TL functions, cached entity resolution and
premium features without every module reinventing ``app.invoke`` plumbing.
"""

from haruka.tl.entities import EntityCache
from haruka.tl.raw import RawAPI

__all__ = ["EntityCache", "RawAPI"]
