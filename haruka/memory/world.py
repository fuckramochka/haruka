from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from haruka.domain import IncomingMessage
from haruka.persistence.database import Database


DEFAULT_WORLD_MEMORY: dict[str, Any] = {
    "chat_history_summaries": [],
    "important_events": [],
    "conflicts": [],
    "community_lore": [],
    "recurring_memes": [],
    "social_structures": {},
}


class WorldMemory:
    def __init__(self, database: Database):
        self.database = database

    async def get_chat(self, chat_id: str) -> dict[str, Any]:
        db = self.database.require()
        cursor = await db.execute(
            "SELECT data_json FROM world_memory WHERE chat_id = ? AND key = 'world'",
            (chat_id,),
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["data_json"])
        memory = dict(DEFAULT_WORLD_MEMORY)
        await self.save_chat(chat_id, memory)
        return memory

    async def has_message(self, chat_id: int, message_id: int) -> bool:
        db = self.database.require()
        cursor = await db.execute(
            "SELECT 1 FROM raw_messages WHERE chat_id = ? AND message_id = ?",
            (str(chat_id), message_id),
        )
        return await cursor.fetchone() is not None

    async def save_chat(self, chat_id: str, memory: dict[str, Any]) -> None:
        db = self.database.require()
        await db.execute(
            """
            INSERT INTO world_memory(chat_id, key, data_json, updated_at)
            VALUES (?, 'world', ?, ?)
            ON CONFLICT(chat_id, key) DO UPDATE SET data_json = excluded.data_json, updated_at = excluded.updated_at
            """,
            (chat_id, json.dumps(memory, ensure_ascii=False), datetime.now(UTC).isoformat()),
        )
        await db.commit()

    async def observe_message(self, message: IncomingMessage) -> None:
        db = self.database.require()
        await db.execute(
            """
            INSERT OR IGNORE INTO raw_messages(chat_id, message_id, sender_id, text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(message.chat_id),
                message.message_id,
                str(message.sender_id) if message.sender_id is not None else None,
                message.text,
                message.created_at.isoformat(),
            ),
        )
        await db.commit()

        text = message.text.lower()
        if any(marker in text for marker in ("лол", "ахах", "haha", " мем", "meme")):
            memory = await self.get_chat(str(message.chat_id))
            memes = memory.setdefault("recurring_memes", [])
            candidate = message.text[:180]
            if candidate not in memes:
                memes.append(candidate)
                memory["recurring_memes"] = memes[-100:]
                await self.save_chat(str(message.chat_id), memory)
