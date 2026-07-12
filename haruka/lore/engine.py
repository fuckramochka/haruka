from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from haruka.domain import IncomingMessage
from haruka.persistence.database import Database


DEFAULT_LORE: dict[str, Any] = {
    "inside_jokes": [],
    "memes": [],
    "important_events": [],
    "conflicts": [],
    "social_structures": [],
}


class LoreEngine:
    def __init__(self, database: Database, lore_dir: Path):
        self.database = database
        self.lore_dir = lore_dir
        self.lore_dir.mkdir(parents=True, exist_ok=True)

    async def get(self, chat_id: int | str) -> dict[str, Any]:
        db = self.database.require()
        cursor = await db.execute("SELECT data_json FROM chat_lore WHERE chat_id = ?", (str(chat_id),))
        row = await cursor.fetchone()
        if row:
            return json.loads(row["data_json"])
        lore = {key: list(value) for key, value in DEFAULT_LORE.items()}
        await self.save(chat_id, lore)
        return lore

    async def observe(self, message: IncomingMessage) -> dict[str, Any]:
        lore = await self.get(message.chat_id)
        text = message.text.strip()
        lower = text.lower()
        now = message.created_at.isoformat()

        if any(marker in lower for marker in ("ахах", "лол", "кек", "рофл", "жиза", "meme", "мем")):
            self._append_lore(lore, "memes", text, now, message)
        if any(marker in lower for marker in ("пам'ятаєте", "помните", "легенда", "історія", "история")):
            self._append_lore(lore, "important_events", text, now, message)
        if any(marker in lower for marker in ("свар", "конфлікт", "конфликт", "драма", "drama")):
            self._append_lore(lore, "conflicts", text, now, message)
        if any(marker in lower for marker in ("наш жарт", "inside", "локальний", "локальный")):
            self._append_lore(lore, "inside_jokes", text, now, message)

        await self.save(message.chat_id, lore)
        return lore

    async def save(self, chat_id: int | str, lore: dict[str, Any]) -> None:
        db = self.database.require()
        now = datetime.now(UTC).isoformat()
        await db.execute(
            """
            INSERT INTO chat_lore(chat_id, data_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET data_json = excluded.data_json, updated_at = excluded.updated_at
            """,
            (str(chat_id), json.dumps(lore, ensure_ascii=False), now),
        )
        await db.commit()
        path = self.lore_dir / f"{chat_id}.json"
        path.write_text(json.dumps({"chat_id": chat_id, **lore}, ensure_ascii=False, indent=2), encoding="utf-8")

    def choose_relevant(self, lore: dict[str, Any], query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_terms = set(query.lower().split())
        candidates: list[tuple[float, dict[str, Any]]] = []
        now = datetime.now(UTC)
        for category, items in lore.items():
            if not isinstance(items, list):
                continue
            for item in items:
                text = str(item.get("text", ""))
                terms = set(text.lower().split())
                lexical = len(query_terms & terms)
                created_at = self._parse_time(item.get("last_seen") or item.get("first_seen"))
                age_days = max(0.0, (now - created_at).total_seconds() / 86400) if created_at else 365.0
                recency = 1.0 / (1.0 + age_days / 14.0)
                frequency = min(2.0, float(item.get("count", 1)) / 3.0)
                nostalgia = 0.25 if age_days > 45 and lexical > 0 else 0.0
                score = lexical * 1.8 + recency * 1.2 + frequency + nostalgia
                candidates.append((score, {"category": category, **item, "score": score}))
        candidates.sort(key=lambda value: value[0], reverse=True)
        return [item for _, item in candidates[:limit]]

    def choose_initiative_seed(self, lore: dict[str, Any]) -> dict[str, Any] | None:
        relevant = self.choose_relevant(lore, query="", limit=12)
        if not relevant:
            return None
        top_recent = relevant[:6]
        old_with_frequency = [item for item in relevant if item.get("count", 1) > 1]
        pool = top_recent + old_with_frequency[:3]
        return random.choice(pool) if pool else None

    def _append_lore(self, lore: dict[str, Any], category: str, text: str, when: str, message: IncomingMessage) -> None:
        items = lore.setdefault(category, [])
        normalized = text.lower()[:160]
        for item in items:
            if item.get("normalized") == normalized:
                item["count"] = int(item.get("count", 1)) + 1
                item["last_seen"] = when
                return
        items.append(
            {
                "text": text[:300],
                "normalized": normalized,
                "first_seen": when,
                "last_seen": when,
                "count": 1,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
            }
        )
        lore[category] = items[-250:]

    @staticmethod
    def _parse_time(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

