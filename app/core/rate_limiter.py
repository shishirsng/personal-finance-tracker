"""Redis-backed rate limiter using fixed window counter."""
from redis.asyncio import Redis
from app.config import get_settings
from app.core.exceptions import RateLimitExceededError
from app.core.logging import get_logger

logger = get_logger("app.core.rate_limiter")
settings = get_settings()


async def check_rate_limit(
    redis: Redis,
    key: str,
    max_requests: int = 5,
    window_seconds: int = 60,
) -> None:
    """
    Enforce rate limit using an atomic Redis counter with TTL.
    Throws RateLimitExceededError when limit is breached.
    In non-production environments, fails open gracefully if Redis is offline.
    """
    try:
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = await pipe.execute()
        current_count: int = results[0]
        ttl: int = results[1]

        if current_count == 1 or ttl == -1:
            await redis.expire(key, window_seconds)

        if current_count > max_requests:
            raise RateLimitExceededError(
                message=f"Rate limit exceeded: maximum {max_requests} requests per {window_seconds}s.",
                details={"retry_after_seconds": max(ttl, 1)},
            )
    except RateLimitExceededError:
        raise
    except Exception as exc:
        if settings.ENVIRONMENT != "production":
            logger.warning("rate_limiter_redis_offline_bypassed", error=str(exc))
            return
        raise
