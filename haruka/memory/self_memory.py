from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from haruka.domain import EmotionState
from haruka.persistence.database import Database


DEFAULT_SELF_MEMORY: dict[str, Any] = {
    "goals": ["exist persistently", "build real relationships", "understand communities"],
    "completed_goals": [],
    "current_projects": ["becoming a believable Telegram participant"],
    "learned_information": [],
    "favorite_chats": [],
    "favorite_users": [],
    "personal_opinions": [],
    "emotional_history": [],
    "achievements": [],
    "failures": [],
    "diary_entries": [],
}


class SelfMemory:
    def __init__(self, database: Database):
        self.database = database

    async def load(self) -> dict[str, Any]:
        db = self.database.require()
        cursor = await db.execute("SELECT data_json FROM self_memory WHERE key = 'notebook'")
        row = await cursor.fetchone()
        if row:
            return json.loads(row["data_json"])
        await self.save(dict(DEFAULT_SELF_MEMORY))
        return dict(DEFAULT_SELF_MEMORY)

    async def save(self, notebook: dict[str, Any]) -> None:
        db = self.database.require()
        await db.execute(
            """
            INSERT INTO self_memory(key, data_json, updated_at)
            VALUES ('notebook', ?, ?)
            ON CONFLICT(key) DO UPDATE SET data_json = excluded.data_json, updated_at = excluded.updated_at
            """,
            (json.dumps(notebook, ensure_ascii=False), datetime.now(UTC).isoformat()),
        )
        await db.commit()

    async def load_emotion_state(self) -> EmotionState:
        db = self.database.require()
        cursor = await db.execute("SELECT data_json FROM self_memory WHERE key = 'emotion_state'")
        row = await cursor.fetchone()
        if not row:
            return EmotionState()
        data = json.loads(row["data_json"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return EmotionState(**data)

    async def save_emotion_state(self, state: EmotionState) -> None:
        data = {
            "mood": state.mood,
            "energy": state.energy,
            "curiosity": state.curiosity,
            "motivation": state.motivation,
            "trust": state.trust,
            "updated_at": state.updated_at.isoformat(),
        }
        db = self.database.require()
        await db.execute(
            """
            INSERT INTO self_memory(key, data_json, updated_at)
            VALUES ('emotion_state', ?, ?)
            ON CONFLICT(key) DO UPDATE SET data_json = excluded.data_json, updated_at = excluded.updated_at
            """,
            (json.dumps(data, ensure_ascii=False), datetime.now(UTC).isoformat()),
        )
        await db.commit()

    async def add_diary_entry(self, text: str) -> None:
        notebook = await self.load()
        notebook.setdefault("diary_entries", []).append(
            {"at": datetime.now(UTC).isoformat(), "text": text}
        )
        notebook["diary_entries"] = notebook["diary_entries"][-500:]
        await self.save(notebook)

    async def record_goal_progress(self, goal: str, note: str) -> None:
        notebook = await self.load()
        notebook.setdefault("current_projects", [])
        notebook.setdefault("achievements", [])
        if goal not in notebook["current_projects"]:
            notebook["current_projects"].append(goal)
        notebook["achievements"].append(
            {"at": datetime.now(UTC).isoformat(), "goal": goal, "note": note}
        )
        notebook["achievements"] = notebook["achievements"][-300:]
        await self.save(notebook)
