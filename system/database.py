import aiosqlite
import json
import logging
import asyncio
import time
from typing import Any, Optional, Callable

# Налаштування логера
logger = logging.getLogger("Database")

class DatabaseError(Exception):
    """Базовий клас помилок бази даних."""
    pass

class ConnectionError(DatabaseError):
    """Помилка підключення."""
    pass

class SerializationError(DatabaseError):
    """Помилка серіалізації даних."""
    pass

class Database:
    def __init__(self, path: str, serializer: Callable = json.dumps, deserializer: Callable = json.loads):
        self.path = path
        self.conn: Optional[aiosqlite.Connection] = None
        
        # Блокування для запису (Write Lock) для уникнення Race Conditions
        self._write_lock = asyncio.Lock()
        
        # Серіалізатори (можна замінити на orjson/ujson при ініціалізації)
        self._dumps = serializer
        self._loads = deserializer
        
        # Ліміт розміру значення (наприклад, 5MB)
        self.MAX_VALUE_SIZE = 5 * 1024 * 1024 

    async def connect(self, timeout: int = 5):
        """
        Підключається до БД, вмикає WAL та виконує міграції структури таблиць.
        """
        if self.conn:
            return

        try:
            async with asyncio.timeout(timeout):
                self.conn = await aiosqlite.connect(self.path)
                
                # [1] WAL Mode для кращої швидкодії
                await self.conn.execute("PRAGMA journal_mode=WAL;")
                await self.conn.execute("PRAGMA synchronous=NORMAL;")
                
                # [2] Створюємо базову таблицю (якщо її ще немає)
                await self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS kv (
                        key TEXT PRIMARY KEY, 
                        value TEXT
                    )
                """)

                # [3] 🔥 МІГРАЦІЯ: Перевіряємо і додаємо колонку expires_at, якщо це стара база
                async with self.conn.execute("PRAGMA table_info(kv)") as cursor:
                    columns = [row[1] for row in await cursor.fetchall()]
                
                if "expires_at" not in columns:
                    logger.warning("🛠 Database migration: Adding 'expires_at' column...")
                    await self.conn.execute("ALTER TABLE kv ADD COLUMN expires_at REAL")

                # [4] Створюємо індекс для швидкого очищення
                await self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_expires ON kv (expires_at)"
                )
                
                await self.conn.commit()
                logger.info(f"Connected to DB at {self.path} (WAL enabled)")
                
        except asyncio.TimeoutError:
            self.conn = None
            raise ConnectionError(f"Timeout connecting to database at {self.path}")
        except Exception as e:
            self.conn = None
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect: {e}")

    async def _ensure_connected(self):
        """Перевіряє з'єднання і намагається перепідключитись."""
        if not self.conn:
            try:
                logger.warning("Connection lost. Attempting to reconnect...")
                await self.connect()
            except Exception as e:
                raise ConnectionError(f"Database unavailable: {e}")

    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None, 
        commit: bool = True
    ):
        """
        Зберігає значення.
        :param ttl: Час життя в секундах.
        :param commit: Чи записувати на диск одразу.
        """
        if not key:
            raise ValueError("Key cannot be empty")
        
        await self._ensure_connected()

        try:
            serialized = self._dumps(value)
        except (TypeError, ValueError) as e:
            raise SerializationError(f"Value for '{key}' is not serializable: {e}")

        if len(serialized) > self.MAX_VALUE_SIZE:
            raise ValueError(f"Value size ({len(serialized)} bytes) exceeds limit")

        # Розрахунок часу вигасання
        expires_at = (time.time() + ttl) if ttl else None

        async with self._write_lock:
            try:
                await self.conn.execute(
                    "INSERT OR REPLACE INTO kv (key, value, expires_at) VALUES (?, ?, ?)", 
                    (key, serialized, expires_at)
                )
                if commit:
                    await self.conn.commit()
            except Exception as e:
                logger.error(f"Write error for '{key}': {e}")
                raise DatabaseError(e)

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Отримує значення. Ігнорує прострочені ключі (Lazy Expiration).
        """
        if not key: 
            return default

        await self._ensure_connected()

        try:
            # Вибираємо тільки якщо ключ існує І (не має терміну дії АБО термін ще не вийшов)
            query = "SELECT value FROM kv WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)"
            current_time = time.time()
            
            async with self.conn.execute(query, (key, current_time)) as cur:
                row = await cur.fetchone()
                
            if row:
                try:
                    return self._loads(row[0])
                except Exception as e:
                    logger.error(f"JSON Corruption for key '{key}': {e}")
                    return default
            return default
            
        except Exception as e:
            logger.error(f"Read error for '{key}': {e}")
            return default

    async def delete(self, key: str, commit: bool = True):
        """Видаляє ключ."""
        await self._ensure_connected()
        
        async with self._write_lock:
            await self.conn.execute("DELETE FROM kv WHERE key = ?", (key,))
            if commit:
                await self.conn.commit()

    async def flush(self):
        """Примусово записує зміни на диск."""
        await self._ensure_connected()
        async with self._write_lock:
            await self.conn.commit()

    async def purge_expired(self):
        """Очищає прострочені ключі."""
        await self._ensure_connected()
        current_time = time.time()
        async with self._write_lock:
            await self.conn.execute("DELETE FROM kv WHERE expires_at < ?", (current_time,))
            await self.conn.commit()

    async def close(self):
        """Безпечно закриває з'єднання."""
        if self.conn:
            try:
                await self.conn.commit()
                await self.conn.close()
            except Exception as e:
                logger.error(f"Error closing DB: {e}")
            finally:
                self.conn = None
                logger.info("Database closed.")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error(f"Database context exit with error: {exc_val}")
        await self.close()

# --- Приклад використання ---
async def example():
    # Можна вказати шлях до файлу
    db = Database("bot_data.db")
    
    async with db:
        print("DB Connected logic starts")
        
        # 1. Звичайний запис
        await db.set("username", "Haruka")
        
        # 2. Запис з TTL (5 секунд)
        await db.set("temp_code", 1234, ttl=5)
        
        # 3. Читання
        print(f"User: {await db.get('username')}")
        print(f"Code: {await db.get('temp_code')}")
        
        # 4. Перевірка видалення часом
        # await asyncio.sleep(6)
        # print(f"Code after sleep: {await db.get('temp_code')}") # Має бути None

if __name__ == "__main__":
    # Налаштуємо логування для тесту
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example())