import asyncio
import shlex
import logging
from .config import Config

logger = logging.getLogger("Context")

class Context:
    def __init__(self, event, engine):
        self.event = event
        self.engine = engine
        self.client = engine.client
        self.db = engine.db
        
        # Parse text arguments safely (handling quotes)
        self.raw_text = event.raw_text or ""
        try:
            self.parts = shlex.split(self.raw_text)
        except ValueError:
            self.parts = self.raw_text.split()
            
        # Determine command trigger (strip prefix)
        prefix_len = len(Config.PREFIX)
        if self.parts and self.parts[0].startswith(Config.PREFIX):
            self.trigger = self.parts[0][prefix_len:]
        else:
            self.trigger = ""
            
        self.args = self.parts[1:]
        
        # Input string (everything after the command trigger)
        cmd_len = len(self.parts[0]) if self.parts else 0
        self.input = self.raw_text[cmd_len:].strip()

    async def respond(self, text: str, delay: int = 0, web_preview: bool = False):
        """
        Universal response method.
        🔥 FORCES HTML PARSING GLOBALLY 🔥
        """
        try:
            if self.event.out:
                # Edit own message
                await self.engine.limiter.execute(
                    self.event.edit, 
                    text, 
                    parse_mode='html',
                    link_preview=web_preview
                )
                msg = self.event
            else:
                # Reply to incoming message
                msg = await self.engine.limiter.execute(
                    self.event.reply, 
                    text, 
                    parse_mode='html',
                    link_preview=web_preview
                )
            
            # Auto-delete functionality
            if delay > 0:
                self.engine.loop.create_task(self._del(msg, delay))
                
        except Exception as e:
            logger.error(f"Error responding: {e}")

    async def _del(self, msg, t):
        await asyncio.sleep(t)
        try: await msg.delete()
        except: pass

    async def get_reply(self):
        """Helper to get reply message object"""
        return await self.event.get_reply_message()

    async def err(self, text: str):
        await self.respond(f"<b>⛔ Error:</b> {text}")

    async def ok(self, text: str):
        await self.respond(f"<b>✅ Success:</b> {text}")
        
    async def warn(self, text: str):
        await self.respond(f"<b>⚠️ Warning:</b> {text}")