import asyncio
import logging
from telethon.errors import FloodWaitError

logger = logging.getLogger("HarukaGuard")

class RateLimiter:
    """
    Automatically catches FloodWait and waits for the required time.
    """
    async def execute(self, func, *args, **kwargs):
        retries = 3
        while retries > 0:
            try:
                return await func(*args, **kwargs)
            except FloodWaitError as e:
                wait_time = e.seconds + 1
                logger.warning(f"⏳ FloodWait: Sleeping for {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                retries -= 1
            except Exception as e:
                # Other errors are propagated further for handling in Dispatcher
                raise e
        raise Exception("API Rate Limit Exceeded")