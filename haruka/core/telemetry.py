from __future__ import annotations

import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from statistics import fmean
from typing import Iterator


@dataclass(slots=True)
class Metrics:
    counters: Counter[str] = field(default_factory=Counter)
    durations: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    gauges: dict[str, float] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] += value

    def gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    @contextmanager
    def timer(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            bucket = self.durations[name]
            bucket.append(time.perf_counter() - started)
            if len(bucket) > 1000:
                del bucket[:-1000]

    def snapshot(self) -> dict[str, object]:
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "latency": {name: {"count": len(values), "mean": fmean(values), "max": max(values)} for name, values in self.durations.items() if values},
        }
