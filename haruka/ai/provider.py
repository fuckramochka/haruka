from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class ModelProvider(abc.ABC):
    @abc.abstractmethod
    async def complete(self, messages: list[ChatMessage]) -> str:
        raise NotImplementedError

