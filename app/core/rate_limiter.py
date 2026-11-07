"""Redis-backed rate limiter using fixed window counter."""
from redis.asyncio import Redis
from app.core.exceptions import RateLimitExceededError


async def check_rate_limit(
    redis: Redis,
    key: str,
    max_requests: int = 5,
    window_seconds: int = 60,
) -> None:
    """
    Enforce rate limit using an atomic Redis counter with TTL.
    Throws RateLimitExceededError when limit is breached.
    """
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    results = await pipe.execute()
    current_count: int = results[0]
    ttl: int = results[1]

    if current_count == 1 or ttl == -1:
        # Set expiration on first hit or if expired key lost TTL
        await redis.expire(key, window_seconds)

    if current_count > max_requests:
        raise RateLimitExceededError(
            message=f"Rate limit exceeded: maximum {max_requests} requests per {window_seconds}s.",
            details={"retry_after_seconds": max(ttl, 1)},
        )
