from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from haruka.domain import IncomingMessage
from haruka.persistence.database import Database


DEFAULT_RELATIONSHIP: dict[str, Any] = {
    "trust": 50.0,
    "friendship": 10.0,
    "interest": 25.0,
    "respect": 50.0,
    "attachment": 5.0,
    "last_interaction": None,
    "interaction_count": 0,
}


class RelationshipEngine:
    def __init__(self, database: Database):
        self.database = database

    async def get(self, person_id: str) -> dict[str, Any]:
        db = self.database.require()
        cursor = await db.execute("SELECT data_json FROM relationships WHERE person_id = ?", (person_id,))
        row = await cursor.fetchone()
        if row:
            return json.loads(row["data_json"])
        return dict(DEFAULT_RELATIONSHIP)

    async def observe(self, message: IncomingMessage) -> dict[str, Any] | None:
        if message.sender_id is None:
            return None
        person_id = str(message.sender_id)
        relationship = await self.get(person_id)
        text = message.text.lower()

        relationship["interaction_count"] = int(relationship.get("interaction_count", 0)) + 1
        relationship["last_interaction"] = message.created_at.isoformat()
        relationship["friendship"] = self._clamp(float(relationship.get("friendship", 10.0)) + 0.45)
        relationship["interest"] = self._clamp(float(relationship.get("interest", 25.0)) + (1.2 if "?" in text else 0.15))
        relationship["attachment"] = self._clamp(float(relationship.get("attachment", 5.0)) + 0.18)

        if any(word in text for word in ("дякую", "спасибо", "thanks", "круто", "приємно", "nice")):
            relationship["trust"] = self._clamp(float(relationship.get("trust", 50.0)) + 1.5)
            relationship["respect"] = self._clamp(float(relationship.get("respect", 50.0)) + 0.8)
        if any(word in text for word in ("туп", "ідіот", "идиот", "stupid", "hate")):
            relationship["trust"] = self._clamp(float(relationship.get("trust", 50.0)) - 2.5)
            relationship["respect"] = self._clamp(float(relationship.get("respect", 50.0)) - 1.5)

        await self.save(person_id, relationship)
        return relationship

    async def save(self, person_id: str, relationship: dict[str, Any]) -> None:
        db = self.database.require()
        now = datetime.now(UTC).isoformat()
        await db.execute(
            """
            INSERT INTO relationships(person_id, data_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET data_json = excluded.data_json, updated_at = excluded.updated_at
            """,
            (person_id, json.dumps(relationship, ensure_ascii=False), now),
        )
        await db.commit()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, value))

