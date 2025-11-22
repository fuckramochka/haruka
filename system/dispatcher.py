import asyncio
import logging
from .config import Config
from .context import Context

logger = logging.getLogger("Dispatcher")

class Dispatcher:
    def __init__(self, engine):
        self.engine = engine

    async def handle(self, event):
        text = event.raw_text
        if not text or not text.startswith(Config.PREFIX):
            return

        trigger = text.split()[0][len(Config.PREFIX):].lower()
        meta = self.engine.registry.commands.get(trigger)
        
        if not meta: return
        
        # Check ownership (security)
        if not event.out and not meta.flags.get('allow_sudo'):
            return

        ctx = Context(event, self.engine)
        try:
            await asyncio.wait_for(meta.handler(ctx), timeout=Config.COMMAND_TIMEOUT)
        except asyncio.TimeoutError:
            await ctx.err("Execution time exceeded!")
        except Exception as e:
            logger.error(f"Crash: {e}", exc_info=True)
            await ctx.err(f"Error: {e}")