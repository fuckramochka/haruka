from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

JsonDict = dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class IncomingMessage:
    message_id: int
    chat_id: int
    sender_id: int | None
    chat_title: str | None
    sender_name: str | None
    sender_username: str | None
    text: str
    is_private: bool
    is_reply_to_haruka: bool
    mentioned_haruka: bool
    created_at: datetime
    # Telegram evolves faster than the engine. New transport metadata is optional.
    thread_id: int | None = None
    business_connection_id: str | None = None
    guest_query_id: str | None = None
    checklist_task_id: int | None = None
    rich_message: JsonDict | None = None
    raw: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class ChatStyleProfile:
    chat_id: int
    vocabulary: list[str] = field(default_factory=list)
    slang: list[str] = field(default_factory=list)
    avg_message_length: float = 0.0
    emoji_rate: float = 0.0
    punctuation: JsonDict = field(default_factory=dict)
    local_memes: list[str] = field(default_factory=list)
    recurring_jokes: list[str] = field(default_factory=list)
    sample_size: int = 0
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class EmotionState:
    mood: str = "neutral"
    energy: float = 0.72
    curiosity: float = 0.66
    motivation: float = 0.58
    trust: float = 0.5
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class ActionDecision:
    action: Literal["observe", "react", "short_response", "long_response"]
    reason: str
    should_reply: bool
    reaction: str | None = None
