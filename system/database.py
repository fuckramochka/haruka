import aiosqlite
import json
from .config import Config

class Database:
    def __init__(self):
        self.path = Config.DB_FILE
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
        await self.conn.commit()

    async def set(self, key, value):
        await self.conn.execute(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", 
            (key, json.dumps(value))
        )
        await self.conn.commit()

    async def get(self, key, default=None):
        async with self.conn.execute("SELECT value FROM kv WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return json.loads(row[0]) if row else default