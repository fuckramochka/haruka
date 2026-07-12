from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToolManager:
    """Placeholder for future Telegram-native tools.

    The Telegram engine already exposes sending messages, reactions, photos,
    stickers, and files. This class is the extension point for higher-level
    policies such as sticker selection, album posting, and filesystem tools.
    """

    enabled: bool = True

