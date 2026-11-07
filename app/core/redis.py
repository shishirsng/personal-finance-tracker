"""Redis connection lifecycle and client singleton."""
from redis.asyncio import ConnectionPool, Redis
from app.config import get_settings

settings = get_settings()

_redis_pool: ConnectionPool | None = None
_redis_client: Redis | None = None


def get_redis_pool() -> ConnectionPool:
    """Return or initialize the global Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.redis_connection_url,
            decode_responses=True,
            max_connections=50,
        )
    return _redis_pool


def get_redis_client() -> Redis:
    """Return or initialize the global async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(connection_pool=get_redis_pool())
    return _redis_client


async def close_redis() -> None:
    """Close the global Redis client and connection pool."""
    global _redis_client, _redis_pool
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
