from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Any

from haruka.persistence.database import Database


class VectorMemory:
    """Lightweight deterministic vector store.

    This is intentionally provider-free so memory works immediately. Production
    deployments can replace `_embed` with a real embedding provider without
    changing repository callers.
    """

    def __init__(self, database: Database, dimensions: int = 64):
        self.database = database
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    async def add(self, scope: str, owner_id: str, text: str, metadata: dict[str, Any]) -> None:
        if not text.strip():
            return
        db = self.database.require()
        await db.execute(
            """
            INSERT OR IGNORE INTO vector_memory(scope, owner_id, text, metadata_json, vector_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                scope,
                owner_id,
                text.strip(),
                json.dumps(metadata, ensure_ascii=False),
                json.dumps(self._embed(text)),
                datetime.now(UTC).isoformat(),
            ),
        )
        await db.commit()

    async def search(self, scope: str, owner_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_vector = self._embed(query)
        db = self.database.require()
        cursor = await db.execute(
            """
            SELECT text, metadata_json, vector_json, created_at
            FROM vector_memory
            WHERE scope = ? AND owner_id = ?
            ORDER BY id DESC
            LIMIT 500
            """,
            (scope, owner_id),
        )
        rows = await cursor.fetchall()
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            vector = json.loads(row["vector_json"])
            semantic = sum(left * right for left, right in zip(query_vector, vector, strict=False))
            created_at = self._parse_time(row["created_at"])
            age_days = max(0.0, (datetime.now(UTC) - created_at).total_seconds() / 86400) if created_at else 365.0
            recency = 1.0 / (1.0 + age_days / 14.0)
            score = semantic * 0.72 + recency * 0.28
            scored.append(
                (
                    score,
                    {
                        "text": row["text"],
                        "metadata": json.loads(row["metadata_json"]),
                        "created_at": row["created_at"],
                        "score": score,
                        "semantic_score": semantic,
                        "recency_score": recency,
                    },
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in scored[:limit]]

    @staticmethod
    def _parse_time(value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
