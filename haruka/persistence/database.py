from __future__ import annotations

from pathlib import Path

import aiosqlite


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA journal_mode=WAL")
        await self.connection.execute("PRAGMA foreign_keys=ON")
        await self.migrate()

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()

    async def migrate(self) -> None:
        db = self.require()
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS people_profiles (
                person_id TEXT PRIMARY KEY,
                display_name TEXT,
                username TEXT,
                data_json TEXT NOT NULL,
                trust_level REAL NOT NULL DEFAULT 0.5,
                friendship_score REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS self_memory (
                key TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS world_memory (
                chat_id TEXT NOT NULL,
                key TEXT NOT NULL,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (chat_id, key)
            );

            CREATE TABLE IF NOT EXISTS chat_style_profiles (
                chat_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS raw_messages (
                chat_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                sender_id TEXT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (chat_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS vector_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_vector_message
            ON vector_memory(scope, owner_id, json_extract(metadata_json, '$.message_id'));

            CREATE INDEX IF NOT EXISTS idx_raw_messages_created
            ON raw_messages(chat_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS relationships (
                person_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                data_json TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                progress REAL NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_lore (
                chat_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        await db.commit()

    def require(self) -> aiosqlite.Connection:
        if not self.connection:
            raise RuntimeError("Database is not open")
        return self.connection
