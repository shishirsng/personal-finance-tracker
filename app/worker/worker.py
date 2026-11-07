"""ARQ worker configuration and lifecycle."""
from typing import Any
from arq.connections import RedisSettings
from arq.cron import cron
from app.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import setup_logging
from app.worker.tasks import flag_stale_accounts

settings = get_settings()


async def startup(ctx: dict[str, Any]) -> None:
    """Worker initialization hook."""
    setup_logging(debug=settings.DEBUG)
    ctx["session_factory"] = async_session_factory


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker teardown hook."""
    pass


class WorkerSettings:
    """ARQ Worker configuration class."""

    functions = [flag_stale_accounts]
    cron_jobs = [
        cron(flag_stale_accounts, hour=0, minute=0),  # Runs daily at midnight UTC
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )
