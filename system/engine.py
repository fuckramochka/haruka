import logging
import asyncio
from telethon import TelegramClient, events
from .config import Config
from .registry import Registry
from .loader import Loader
from .dispatcher import Dispatcher
from .database import Database
from .ratelimit import RateLimiter

# Logging to console (User Friendly)
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class Engine:
    def __init__(self):
        # Create client with hardcoded data
        self.client = TelegramClient(Config.SESSION_NAME, Config.API_ID, Config.API_HASH)
        self.loop = asyncio.get_event_loop()
        
        # Initialize components
        self.db = Database()
        self.registry = Registry()
        self.loader = Loader(self)
        self.dispatcher = Dispatcher(self)
        self.limiter = RateLimiter()
        
        # Connect events
        self.client.add_event_handler(self.dispatcher.handle, events.NewMessage())

    async def start(self):
        print("🌸 Haruka v4 Plug-and-Play is starting...")
        
        # 1. Authorization (interactive in console if needed)
        await self.client.start()
        
        # 2. Database connection
        await self.db.connect()
        
        # 3. Loading modules
        await self.loader.load_all()
        
        me = await self.client.get_me()
        print(f"\n✅ Successful login as: {me.first_name} (@{me.username})")
        print(f"⚡️ Command prefix: {Config.PREFIX}")
        print(f"📂 Plugins folder: {Config.PLUGINS_DIR}\n")
        
        await self.client.run_until_disconnected()