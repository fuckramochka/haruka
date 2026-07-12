"""Composable Haruka engine primitives.

Runtime is imported lazily so lightweight SDK modules do not require Telegram
or database dependencies at import time.
"""

from typing import Any

__all__ = ["HarukaRuntime"]


def __getattr__(name: str) -> Any:
    if name == "HarukaRuntime":
        from haruka.core.runtime import HarukaRuntime
        return HarukaRuntime
    raise AttributeError(name)
