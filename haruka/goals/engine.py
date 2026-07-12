from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal

from haruka.domain import IncomingMessage
from haruka.persistence.database import Database

GoalStatus = Literal["active", "paused", "completed", "abandoned"]


@dataclass(slots=True)
class Goal:
    title: str
    progress: float = 0.0
    status: GoalStatus = "active"
    priority: int = 2
    created_at: str = ""
    updated_at: str = ""
    notes: list[str] | None = None


class GoalEngine:
    def __init__(self, database: Database):
        self.database = database

    async def ensure_defaults(self) -> None:
        await self.upsert(Goal("Learn new memes from chats", progress=5.0, priority=2))
        await self.upsert(Goal("Build distinct relationships with regular users", progress=8.0, priority=1))
        await self.upsert(Goal("Preserve Haruka identity across restarts", progress=40.0, priority=1))

    async def upsert(self, goal: Goal) -> None:
        now = datetime.now(UTC).isoformat()
        if not goal.created_at:
            goal.created_at = now
        goal.updated_at = now
        if goal.notes is None:
            goal.notes = []
        db = self.database.require()
        await db.execute(
            """
            INSERT INTO goals(title, data_json, status, priority, progress, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                data_json = excluded.data_json,
                status = excluded.status,
                priority = excluded.priority,
                progress = excluded.progress,
                updated_at = excluded.updated_at
            """,
            (
                goal.title,
                json.dumps(asdict(goal), ensure_ascii=False),
                goal.status,
                goal.priority,
                goal.progress,
                goal.updated_at,
            ),
        )
        await db.commit()

    async def active_goals(self, limit: int = 5) -> list[Goal]:
        db = self.database.require()
        cursor = await db.execute(
            """
            SELECT data_json FROM goals
            WHERE status = 'active'
            ORDER BY priority ASC, progress ASC, updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [Goal(**json.loads(row["data_json"])) for row in rows]

    async def observe(self, message: IncomingMessage) -> None:
        await self.ensure_defaults()
        lower = message.text.lower()
        if any(marker in lower for marker in ("мем", "meme", "лол", "жиза", "рофл")):
            await self.advance("Learn new memes from chats", 3.0, f"noticed possible meme: {message.text[:120]}")
        if message.sender_id is not None:
            await self.advance(
                "Build distinct relationships with regular users",
                0.5,
                f"observed interaction with {message.sender_name or message.sender_id}",
            )

    async def advance(self, title: str, amount: float, note: str) -> None:
        goal = await self.get(title)
        if goal is None:
            goal = Goal(title=title)
        goal.progress = min(100.0, max(0.0, goal.progress + amount))
        if goal.progress >= 100.0:
            goal.status = "completed"
        notes = goal.notes or []
        notes.append(f"{datetime.now(UTC).isoformat()}: {note}")
        goal.notes = notes[-50:]
        await self.upsert(goal)

    async def get(self, title: str) -> Goal | None:
        db = self.database.require()
        cursor = await db.execute("SELECT data_json FROM goals WHERE title = ?", (title,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Goal(**json.loads(row["data_json"]))

    async def choose_initiative_goal(self) -> Goal | None:
        goals = await self.active_goals(limit=10)
        if not goals:
            return None
        weighted = sorted(goals, key=lambda goal: (goal.priority, goal.progress))
        top = weighted[:3]
        return random.choice(top)

