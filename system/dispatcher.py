import asyncio
import logging
import time
from typing import Dict, Optional
from .config import Config
from .context import Context

logger = logging.getLogger("Dispatcher")

class Dispatcher:
    def __init__(self, engine):
        self.engine = engine
        # [9] Simple in-memory cooldown: user_id -> last_command_time
        self._cooldowns: Dict[int, float] = {}
        self.COOLDOWN_RATE = 0.5  # Seconds between commands for one user

    async def handle(self, event):
        # [1] Validation: Check for empty text or None
        text = getattr(event, 'raw_text', "")
        if not text or not text.strip():
            return

        # [10] Unicode Normalization & [2] Casing
        # Handles multi-prefix logic explicitly
        prefixes = Config.PREFIX if isinstance(Config.PREFIX, list) else [Config.PREFIX]
        matched_prefix = None
        
        for p in prefixes:
            if text.startswith(p):
                matched_prefix = p
                break
        
        if not matched_prefix:
            return

        # Extract trigger: "!ping arg" -> "ping"
        # .split(maxsplit=1) is more efficient than full split
        try:
            trigger_part = text[len(matched_prefix):].lstrip().split(maxsplit=1)[0]
            trigger = trigger_part.casefold() # [10] Stronger than .lower() for unicode
        except IndexError:
            return

        # [3] Safe Registry Access (assuming Registry has get_command method)
        # Using public API instead of accessing .commands dict directly
        meta = await self.engine.registry.get_command(trigger)
        
        if not meta:
            return

        # [4] Security: Ownership Check
        # Explicit .get(..., False) ensures secure default
        if not event.out and not meta.flags.get('allow_sudo', False):
            return

        # [9] Rate Limiting / Cooldown Check
        sender_id = event.sender_id
        if sender_id:
            current_time = time.time()
            last_time = self._cooldowns.get(sender_id, 0)
            if current_time - last_time < self.COOLDOWN_RATE:
                # Silently ignore spam or log it
                return
            self._cooldowns[sender_id] = current_time

        # [5] Context Creation (Lazy)
        # Only created after we know the command exists and is allowed
        ctx = Context(event, self.engine)
        if not ctx.valid:
            return

        # [7] Enhanced Contextual Logging
        chat_id = event.chat_id
        logger.info(f"Command '{trigger}' called by user {sender_id} in chat {chat_id}")

        # Execution Block
        try:
            # [6] Timeout & Task Management
            # We use wait_for to enforce Config limits
            await asyncio.wait_for(
                meta.handler(ctx), 
                timeout=Config.COMMAND_TIMEOUT
            )
        
        except asyncio.TimeoutError:
            logger.warning(f"Command '{trigger}' timed out for user {sender_id}")
            await self._safe_err(ctx, "Execution time exceeded (Timeout).")
            
        except Exception as e:
            # [7] Full Traceback with Context
            logger.error(
                f"Crash in command '{trigger}' (User: {sender_id}): {e}", 
                exc_info=True
            )
            # [8] Safe error reporting
            await self._safe_err(ctx, f"Internal Error: {e}")

    async def _safe_err(self, ctx: Context, message: str):
        """
        [8] Helper to safely send error messages.
        Prevents recursion if the error reporting itself fails.
        """
        try:
            await ctx.err(message)
        except Exception as send_e:
            logger.error(f"Failed to send error message to user: {send_e}")