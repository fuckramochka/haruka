"""Automation engine: triggers + scheduled jobs.

Triggers are pattern -> action rules that fire on incoming/outgoing messages.
Jobs are interval-based tasks that send a message to a chat on a schedule.

Both are persisted in the database (owner ``automation``) so they survive
restarts. The engine registers its own lightweight message handler rather than
piggy-backing on module watchers, keeping automation self-contained.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

if TYPE_CHECKING:
    from haruka.core.app import Application

logger = logging.getLogger(__name__)


@dataclass
class Trigger:
    id: str
    pattern: str
    reply: str
    mode: str = "contains"  # contains | exact | regex
    scope: str = "all"      # all | groups | private
    incoming: bool = True
    outgoing: bool = False

    def matches(self, text: str) -> bool:
        if not text or len(text) > 16_384 or len(self.pattern) > 512:
            return False
        if self.mode == "exact":
            return text.strip().lower() == self.pattern.lower()
        if self.mode == "regex":
            try:
                return re.search(self.pattern, text, re.IGNORECASE) is not None
            except re.error:
                return False
        return self.pattern.lower() in text.lower()


@dataclass
class Job:
    id: str
    chat_id: int
    text: str
    interval: int  # seconds
    next_run: float = 0.0
    enabled: bool = True


@dataclass
class _State:
    triggers: dict[str, Trigger] = field(default_factory=dict)
    jobs: dict[str, Job] = field(default_factory=dict)


class AutomationEngine:
    def __init__(self, app: "Application"):
        self.app = app
        self.db = app.db
        self.client = app.client
        self._state = _State()
        self.fired_count = 0
        self._scheduler_task: Optional[asyncio.Task] = None
        self._handler = None

    # -- persistence -----------------------------------------------------

    def _load(self) -> None:
        raw_triggers = self.db.get("automation", "triggers", {}) or {}
        raw_jobs = self.db.get("automation", "jobs", {}) or {}
        self._state.triggers = {
            tid: Trigger(**data) for tid, data in raw_triggers.items()
        }
        self._state.jobs = {jid: Job(**data) for jid, data in raw_jobs.items()}

    async def _save_triggers(self) -> None:
        await self.db.set(
            "automation",
            "triggers",
            {t.id: t.__dict__ for t in self._state.triggers.values()},
        )

    async def _save_jobs(self) -> None:
        await self.db.set(
            "automation",
            "jobs",
            {j.id: j.__dict__ for j in self._state.jobs.values()},
        )

    # -- lifecycle -------------------------------------------------------

    async def start(self) -> None:
        self._load()
        self._handler = MessageHandler(
            self._on_message, filters.text & ~filters.service
        )
        self.client.app.add_handler(self._handler, group=1)
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info(
            "Automation: %d triggers, %d jobs",
            len(self._state.triggers),
            len(self._state.jobs),
        )

    async def stop(self) -> None:
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        if self._handler is not None:
            self.client.app.remove_handler(self._handler, group=1)
            self._handler = None

    # -- read-only views (used by Control Center) ------------------------

    @property
    def triggers(self) -> dict[str, Trigger]:
        return self._state.triggers

    @property
    def jobs(self) -> dict[str, Job]:
        return self._state.jobs

    # -- trigger management ---------------------------------------------

    async def add_trigger(self, trigger: Trigger) -> None:
        self._state.triggers[trigger.id] = trigger
        await self._save_triggers()

    async def remove_trigger(self, trigger_id: str) -> bool:
        if trigger_id in self._state.triggers:
            del self._state.triggers[trigger_id]
            await self._save_triggers()
            return True
        return False

    # -- job management --------------------------------------------------

    async def add_job(self, job: Job) -> None:
        if job.interval < 60:
            raise ValueError("Job interval must be at least 60 seconds")
        job.next_run = time.time() + job.interval
        self._state.jobs[job.id] = job
        await self._save_jobs()

    async def remove_job(self, job_id: str) -> bool:
        if job_id in self._state.jobs:
            del self._state.jobs[job_id]
            await self._save_jobs()
            return True
        return False

    # -- runtime ---------------------------------------------------------

    async def _on_message(self, _, message: Message) -> None:
        text = message.text or ""
        is_group = message.chat and message.chat.type.name in {"GROUP", "SUPERGROUP"}
        is_private = message.chat and message.chat.type.name == "PRIVATE"

        for trigger in list(self._state.triggers.values()):
            if message.outgoing and not trigger.outgoing:
                continue
            if not message.outgoing and not trigger.incoming:
                continue
            if trigger.scope == "groups" and not is_group:
                continue
            if trigger.scope == "private" and not is_private:
                continue
            if trigger.matches(text):
                try:
                    await message.reply_text(trigger.reply)
                    self.fired_count += 1
                except Exception:
                    logger.exception("Trigger %s failed to reply", trigger.id)
                break  # one trigger per message

    async def _scheduler_loop(self) -> None:
        while True:
            try:
                now = time.time()
                dirty = False
                for job in list(self._state.jobs.values()):
                    if not job.enabled or now < job.next_run:
                        continue
                    try:
                        await self.client.app.send_message(job.chat_id, job.text)
                        self.fired_count += 1
                    except Exception:
                        logger.exception("Job %s failed", job.id)
                    job.next_run = max(job.next_run + job.interval, now + 1)
                    dirty = True
                if dirty:
                    await self._save_jobs()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scheduler loop error")
            await asyncio.sleep(5)
