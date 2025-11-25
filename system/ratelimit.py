import asyncio
import logging
import time
from typing import Callable, Any, Optional
from telethon.errors import FloodWaitError

logger = logging.getLogger("RateLimiter")

class RateLimitExceededError(Exception):
    """Custom exception raised when retries are exhausted or wait time is too long."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error

class RateLimiter:
    """
    Advanced wrapper for handling Telethon FloodWait errors.
    """
    def __init__(
        self, 
        max_retries: int = 5, 
        max_delay_per_request: int = 300,  # Max 5 minutes per single wait
        max_total_wait: int = 600          # Max 10 minutes total per execution
    ):
        self.max_retries = max_retries
        self.max_delay_per_request = max_delay_per_request
        self.max_total_wait = max_total_wait

    async def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Executes an async function with FloodWait handling.
        """
        # [10] Validate that the function is actually a coroutine
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"'{func.__name__}' is not a coroutine function. Use 'async def'.")

        func_name = func.__name__
        attempt = 0
        start_time = time.time()
        
        # [7] Debug log with truncated args to identify the call context
        arg_preview = f"{args[:2]}..." if args else "()"
        logger.debug(f"Executing {func_name}{arg_preview}")

        while attempt <= self.max_retries:
            try:
                # [4] Note: Function logic must be idempotent if possible!
                return await func(*args, **kwargs)

            except FloodWaitError as e:
                wait_time = e.seconds
                
                # [2] Check if single wait is too long
                if wait_time > self.max_delay_per_request:
                    logger.error(f"⛔ FloodWait {wait_time}s exceeds limit per request ({self.max_delay_per_request}s) in {func_name}")
                    raise RateLimitExceededError(f"FloodWait too long: {wait_time}s", e)

                # [8] Check cumulative wait time
                total_elapsed = time.time() - start_time
                if total_elapsed + wait_time > self.max_total_wait:
                    logger.error(f"⛔ Total wait time limit ({self.max_total_wait}s) exceeded in {func_name}")
                    raise RateLimitExceededError("Total wait time exceeded", e)
                
                # [1] Retry logic
                attempt += 1
                if attempt > self.max_retries:
                    logger.error(f"⛔ Max retries ({self.max_retries}) reached for {func_name}")
                    raise RateLimitExceededError("Max retries exceeded", e)

                logger.warning(
                    f"⏳ FloodWait in '{func_name}': Sleeping {wait_time}s "
                    f"(Attempt {attempt}/{self.max_retries})"
                )
                
                # [3] Async sleep does not block the event loop, but blocks this specific task
                await asyncio.sleep(wait_time)

            except Exception as e:
                # [6] Log unexpected errors before propagating
                logger.error(f"💥 Critical error in '{func_name}': {e}")
                raise e

        # Should strictly be unreachable due to the loop condition and raise inside
        raise RateLimitExceededError("Unknown execution flow error")