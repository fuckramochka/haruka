"""Typed async key-value store on top of SQLite.

Replaces the old JSON-blob database. Values are JSON-serialised, namespaced
by owner (usually a module name), and read through an in-memory cache so hot
paths never hit disk.

Usage::

    db = Database(path)
    await db.connect()
    await db.set("MyModule", "greeting", "hello")
    db.get("MyModule", "greeting", default="hi")
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import os
from pathlib import Path
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    owner TEXT NOT NULL,
    key   TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (owner, key)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    actor INTEGER,
    chat_id INTEGER,
    action TEXT NOT NULL,
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log (ts);
"""


class Database:
    """Async SQLite key-value store with a write-through memory cache."""

    def __init__(self, path: Path):
        self._path = path
        self._conn: Optional[aiosqlite.Connection] = None
        self._cache: dict[tuple[str, str], Any] = {}
        self._lock = asyncio.Lock()

    # -- lifecycle -----------------------------------------------------

    async def connect(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        await self._conn.executescript(_SCHEMA)
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA synchronous=NORMAL")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._conn.commit()
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            logger.debug("Could not tighten database permissions", exc_info=True)
        await self._warm_cache()
        logger.info("Database ready at %s (%d keys cached)", self._path, len(self._cache))

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _warm_cache(self) -> None:
        assert self._conn is not None
        async with self._conn.execute("SELECT owner, key, value FROM kv") as cursor:
            async for owner, key, raw in cursor:
                try:
                    self._cache[(owner, key)] = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Dropping corrupt db entry %s/%s", owner, key)

    # -- key-value API ---------------------------------------------------

    def get(self, owner: str, key: str, default: Any = None) -> Any:
        """Synchronous cached read."""
        return self._cache.get((owner, key), default)

    def keys(self, owner: str) -> list[str]:
        return [k for (o, k) in self._cache if o == owner]

    def all(self, owner: str) -> dict[str, Any]:
        return {k: v for (o, k), v in self._cache.items() if o == owner}

    async def set(self, owner: str, key: str, value: Any) -> None:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        raw = json.dumps(value, ensure_ascii=False, default=str)
        async with self._lock:
            await self._conn.execute(
                "INSERT INTO kv (owner, key, value, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(owner, key) DO UPDATE SET value=excluded.value, "
                "updated_at=excluded.updated_at",
                (owner, key, raw, time.time()),
            )
            await self._conn.commit()
            self._cache[(owner, key)] = json.loads(raw)

    async def delete(self, owner: str, key: str) -> bool:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        async with self._lock:
            existed = (owner, key) in self._cache
            await self._conn.execute("DELETE FROM kv WHERE owner=? AND key=?", (owner, key))
            await self._conn.commit()
            self._cache.pop((owner, key), None)
        return existed

    async def wipe_owner(self, owner: str) -> None:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        async with self._lock:
            await self._conn.execute("DELETE FROM kv WHERE owner=?", (owner,))
            await self._conn.commit()
            for cache_key in [ck for ck in self._cache if ck[0] == owner]:
                del self._cache[cache_key]


    async def set_many(self, owner: str, values: dict[str, Any]) -> None:
        """Atomically persist multiple values under one owner."""
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        now = time.time()
        rows = []
        for key, value in values.items():
            raw = json.dumps(value, ensure_ascii=False, default=str)
            rows.append((owner, key, raw, now))
        async with self._lock:
            await self._conn.execute("BEGIN")
            try:
                await self._conn.executemany(
                    "INSERT INTO kv (owner, key, value, updated_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(owner, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    rows,
                )
                await self._conn.commit()
            except Exception:
                await self._conn.rollback()
                raise
            for _, key, raw, _ in rows:
                self._cache[(owner, key)] = json.loads(raw)

    async def prune_audit(self, keep: int = 5000) -> int:
        """Keep the newest audit records and return the number removed."""
        if self._conn is None or keep < 0:
            return 0
        async with self._lock:
            cursor = await self._conn.execute(
                "DELETE FROM audit_log WHERE id NOT IN "
                "(SELECT id FROM audit_log ORDER BY id DESC LIMIT ?)",
                (keep,),
            )
            await self._conn.commit()
        return max(cursor.rowcount, 0)

    # -- audit log -------------------------------------------------------

    async def audit(
        self,
        action: str,
        detail: str = "",
        actor: Optional[int] = None,
        chat_id: Optional[int] = None,
    ) -> None:
        if self._conn is None:
            return
        async with self._lock:
            await self._conn.execute(
                "INSERT INTO audit_log (ts, actor, chat_id, action, detail) VALUES (?, ?, ?, ?, ?)",
                (time.time(), actor, chat_id, action, detail[:2000]),
            )
            await self._conn.commit()

    async def audit_tail(self, limit: int = 20) -> list[dict[str, Any]]:
        if self._conn is None:
            return []
        async with self._conn.execute(
            "SELECT ts, actor, chat_id, action, detail FROM audit_log "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            {"ts": r[0], "actor": r[1], "chat_id": r[2], "action": r[3], "detail": r[4]}
            for r in rows
        ]

    # -- export / import (used by encrypted backups) -----------------------

    def export_all(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for (owner, key), value in self._cache.items():
            out.setdefault(owner, {})[key] = value
        return out

    async def import_all(self, data: dict[str, dict[str, Any]]) -> int:
        count = 0
        for owner, entries in data.items():
            await self.set_many(owner, entries)
            count += len(entries)
        return count
