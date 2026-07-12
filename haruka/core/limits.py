from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimit:
    requests: int
    period_seconds: float


class SlidingWindowLimiter:
    """Concurrency-safe per-key limiter; products choose their own policy."""

    def __init__(self, default: RateLimit):
        self.default = default
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str, limit: RateLimit | None = None) -> bool:
        policy = limit or self.default
        now = time.monotonic()
        cutoff = now - policy.period_seconds
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= policy.requests:
                return False
            events.append(now)
            if not events:
                self._events.pop(key, None)
            return True
