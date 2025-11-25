import logging
import asyncio
import sys
from telethon import TelegramClient, events
from .config import Config
from .registry import Registry
from .loader import Loader
from .dispatcher import Dispatcher
from .database import Database
from .ratelimit import RateLimiter

# [8] Specific logger for Engine
logger = logging.getLogger("Haruka.Engine")

class Engine:
    def __init__(self):
        # Initialize client without starting it yet
        self.client = TelegramClient(Config.SESSION_NAME, Config.API_ID, Config.API_HASH)
        
        # [1] Do not cache get_event_loop() early, rely on running loop
        
        # [2] Explicitly pass DB_FILE
        self.db = Database(path=Config.DB_FILE)
        
        # Initialize Core Components
        self.registry = Registry()
        self.loader = Loader(self)
        self.dispatcher = Dispatcher(self)
        self.limiter = RateLimiter(
            max_retries=3,
            max_delay_per_request=300
        )
        
        # Connect Event Handler
        # [4] Dispatcher.handle already contains internal try/except wrappers
        self.client.add_event_handler(self.dispatcher.handle, events.NewMessage())

    async def _background_maintenance(self):
        """[6] Periodic background tasks (DB Purge, etc.)"""
        logger.info("Maintenance task started.")
        while True:
            try:
                # Run cleanup every hour
                await asyncio.sleep(3600)
                if hasattr(self.db, 'purge_expired'):
                    await self.db.purge_expired()
                    logger.debug("Database TTL purge completed.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance task error: {e}")
                await asyncio.sleep(60) # Wait a bit before retry

    async def start(self):
        print("🌸 Haruka New is starting...")

        # [7] Headless check
        if not sys.stdin.isatty() and not await self._check_session_exists():
            logger.warning("⚠️ Running in headless mode without a session file! Interactive login may fail.")

        try:
            # 1. Authorization
            await self.client.start()
            
            # 2. Database Connection
            await self.db.connect()
            
            # 3. Load Modules with Error Handling
            # [3] Wrapped in try/except
            try:
                await self.loader.load_all()
            except Exception as e:
                logger.error(f"Failed to load plugins: {e}", exc_info=True)
                # We continue execution even if plugins fail, to allow hot-fix or debug

            # 4. Start Background Tasks
            # [6] Create task before blocking run
            bg_task = asyncio.create_task(self._background_maintenance())

            # User Info Display
            me = await self.client.get_me()
            info_text = (
                f"\n✅ Successful login as: {me.first_name} (@{me.username})\n"
                f"⚡️ Command prefix: {Config.PREFIX}\n"
                f"📂 Plugins folder: {Config.PLUGINS_DIR}\n"
                f"💾 Database: {Config.DB_FILE}\n"
            )
            print(info_text)
            logger.info("Haruka New started successfully.")

            # 5. Run Forever
            await self.client.run_until_disconnected()

        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Stopping Haruka New...")
        except Exception as e:
            logger.critical(f"Fatal Engine Error: {e}", exc_info=True)
        finally:
            # Graceful Shutdown
            if 'bg_task' in locals():
                bg_task.cancel()
            
            await self.db.close()
            logger.info("Database connection closed. Goodbye!")

    async def _check_session_exists(self):
        """Helper to check if session file exists (approximate check)."""
        import os
        return os.path.exists(f"{Config.SESSION_NAME}.session")

# [1] Entry point using asyncio.run()
if __name__ == "__main__":
    # Setup basic logging format if run directly
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    engine = Engine()
    try:
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        pass