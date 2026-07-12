from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from haruka.domain import IncomingMessage
from haruka.persistence.database import Database


DEFAULT_PROFILE: dict[str, Any] = {
    "name": None,
    "nicknames": [],
    "interests": [],
    "favorite_topics": [],
    "relationship_status": "acquaintance",
    "communication_style": {},
    "important_events": [],
    "inside_jokes": [],
    "likes": [],
    "dislikes": [],
    "trust_level": 0.5,
    "friendship_score": 0.0,
}


class PeopleMemory:
    def __init__(self, database: Database):
        self.database = database

    async def get(self, person_id: str) -> dict[str, Any]:
        db = self.database.require()
        cursor = await db.execute("SELECT data_json FROM people_profiles WHERE person_id = ?", (person_id,))
        row = await cursor.fetchone()
        if row:
            return json.loads(row["data_json"])
        return dict(DEFAULT_PROFILE)

    async def observe_message(self, message: IncomingMessage) -> dict[str, Any] | None:
        if message.sender_id is None:
            return None
        person_id = str(message.sender_id)
        profile = await self.get(person_id)
        profile["name"] = message.sender_name or profile.get("name")
        if message.sender_username:
            nicknames = set(profile.get("nicknames", []))
            nicknames.add(message.sender_username)
            profile["nicknames"] = sorted(nicknames)

        style = profile.setdefault("communication_style", {})
        style["last_message_length"] = len(message.text)
        style["uses_emoji"] = any(ord(char) > 10000 for char in message.text)
        style["lowercase_bias"] = message.text == message.text.lower()
        style["question_rate_hint"] = "?" in message.text

        profile["friendship_score"] = min(1.0, float(profile.get("friendship_score", 0.0)) + 0.002)
        await self.save(person_id, profile, message.sender_name, message.sender_username)
        return profile

    async def save(
        self,
        person_id: str,
        profile: dict[str, Any],
        display_name: str | None = None,
        username: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        db = self.database.require()
        await db.execute(
            """
            INSERT INTO people_profiles(person_id, display_name, username, data_json, trust_level, friendship_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET
                display_name = excluded.display_name,
                username = excluded.username,
                data_json = excluded.data_json,
                trust_level = excluded.trust_level,
                friendship_score = excluded.friendship_score,
                updated_at = excluded.updated_at
            """,
            (
                person_id,
                display_name,
                username,
                json.dumps(profile, ensure_ascii=False),
                float(profile.get("trust_level", 0.5)),
                float(profile.get("friendship_score", 0.0)),
                now,
            ),
        )
        await db.commit()

