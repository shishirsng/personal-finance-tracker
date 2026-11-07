"""Redis connection lifecycle and client singleton with dev fallback."""
from fakeredis.aioredis import FakeRedis
from redis.asyncio import ConnectionPool, Redis
from app.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("app.core.redis")

_redis_pool: ConnectionPool | None = None
_redis_client: Redis | None = None
_using_fake_redis: bool = False


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
    """Return or initialize the async Redis client, with transparent FakeRedis fallback."""
    global _redis_client, _redis_pool, _using_fake_redis
    if _redis_client is None:
        try:
            _redis_client = Redis(connection_pool=get_redis_pool())
        except Exception as e:
            logger.warning("redis_connection_init_fallback", error=str(e))
            _redis_client = FakeRedis(decode_responses=True)
            _using_fake_redis = True
    return _redis_client


def set_fake_redis() -> None:
    """Explicitly switch to in-memory FakeRedis."""
    global _redis_client, _using_fake_redis
    _redis_client = FakeRedis(decode_responses=True)
    _using_fake_redis = True


async def close_redis() -> None:
    """Close the global Redis client and connection pool."""
    global _redis_client, _redis_pool, _using_fake_redis
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
    _using_fake_redis = False
