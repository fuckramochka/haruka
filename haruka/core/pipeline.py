from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from haruka.domain import IncomingMessage

Next = Callable[["PipelineContext"], Awaitable[None]]


@dataclass(slots=True)
class PipelineContext:
    message: IncomingMessage
    raw: object
    values: dict[str, Any] = field(default_factory=dict)
    stopped: bool = False
    stop_reason: str | None = None

    def stop(self, reason: str) -> None:
        self.stopped = True
        self.stop_reason = reason


class Middleware(Protocol):
    async def __call__(self, context: PipelineContext, call_next: Next) -> None: ...


class MessagePipeline:
    """Composable ingestion pipeline: policy, dedupe, enrichment, cognition, output."""

    def __init__(self) -> None:
        self._middleware: list[Middleware] = []

    def use(self, middleware: Middleware) -> "MessagePipeline":
        self._middleware.append(middleware)
        return self

    async def run(self, context: PipelineContext, terminal: Next) -> PipelineContext:
        async def invoke(index: int, current: PipelineContext) -> None:
            if current.stopped:
                return
            if index == len(self._middleware):
                await terminal(current)
                return
            await self._middleware[index](current, lambda value: invoke(index + 1, value))
        await invoke(0, context)
        return context
