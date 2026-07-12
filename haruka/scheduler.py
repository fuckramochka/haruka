from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self):
        self.tasks: list[asyncio.Task] = []

    def every(self, seconds: int, job: Callable[[], Awaitable[None]], name: str) -> None:
        async def loop() -> None:
            while True:
                try:
                    await job()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Scheduled job failed: %s", name)
                await asyncio.sleep(seconds)

        self.tasks.append(asyncio.create_task(loop(), name=name))

    async def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

