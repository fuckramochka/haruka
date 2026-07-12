from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpen(RuntimeError):
    pass


@dataclass(slots=True)
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_seconds: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    opened_at: float = 0.0

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        now = time.monotonic()
        if self.state is CircuitState.OPEN:
            if now - self.opened_at < self.recovery_seconds:
                raise CircuitOpen("dependency circuit is open")
            self.state = CircuitState.HALF_OPEN
        try:
            result = await operation()
        except asyncio.CancelledError:
            raise
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
            raise
        self.failures = 0
        self.state = CircuitState.CLOSED
        return result
