import pytest

from haruka.core.limits import RateLimit, SlidingWindowLimiter


@pytest.mark.asyncio
async def test_limiter() -> None:
    limiter = SlidingWindowLimiter(RateLimit(2, 60))
    assert await limiter.allow("chat")
    assert await limiter.allow("chat")
    assert not await limiter.allow("chat")
    assert await limiter.allow("other")
