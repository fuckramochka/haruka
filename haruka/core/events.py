from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

logger = logging.getLogger(__name__)
T = TypeVar("T")
EventHandler = Callable[[Any], Awaitable[None] | None]


@dataclass(slots=True)
class Event(Generic[T]):
    topic: str
    payload: T
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Subscription:
    topic: str
    handler: EventHandler
    priority: int
    name: str
    timeout: float


@dataclass(slots=True)
class DispatchReport:
    event_id: str
    handled: int = 0
    failed: dict[str, str] = field(default_factory=dict)


class EventBus:
    """Priority event bus with wildcard subscriptions and failure isolation."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)

    def subscribe(self, topic: str, handler: EventHandler, *, priority: int = 100, name: str | None = None, timeout: float = 15.0) -> Callable[[], None]:
        sub = Subscription(topic, handler, priority, name or getattr(handler, "__qualname__", repr(handler)), timeout)
        self._subscriptions[topic].append(sub)
        self._subscriptions[topic].sort(key=lambda item: item.priority)

        def unsubscribe() -> None:
            if sub in self._subscriptions.get(topic, []):
                self._subscriptions[topic].remove(sub)
        return unsubscribe

    async def publish(self, event: Event[Any]) -> DispatchReport:
        report = DispatchReport(event.id)
        subscriptions = [*self._subscriptions.get(event.topic, []), *self._subscriptions.get("*", [])]
        for sub in sorted(subscriptions, key=lambda item: item.priority):
            try:
                result = sub.handler(event)
                if inspect.isawaitable(result):
                    await asyncio.wait_for(result, timeout=sub.timeout)
                report.handled += 1
            except Exception as exc:
                report.failed[sub.name] = f"{type(exc).__name__}: {exc}"
                logger.exception("Event handler %s failed for %s", sub.name, event.topic)
        return report
