"""FastAPI application factory, lifespan management, and router mounting."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.v1.ops import router as ops_router
from app.api.v1.router import api_v1_router
from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestIDAndLoggingMiddleware, setup_exception_handlers
from app.core.redis import close_redis, get_redis_client

settings = get_settings()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and graceful shutdown."""
    setup_logging(debug=settings.DEBUG)
    logger.info("app_startup", project=settings.PROJECT_NAME, environment=settings.ENVIRONMENT)

    # Pre-warm Redis connection
    redis = get_redis_client()
    try:
        await redis.ping()
        logger.info("redis_connected", host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    except Exception as exc:
        logger.warning("redis_connection_warning", error=str(exc))

    yield

    logger.info("app_shutdown_initiating")
    await close_redis()
    logger.info("app_shutdown_completed")


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Structured logging and Request ID middleware
    app.add_middleware(RequestIDAndLoggingMiddleware)

    # 2. Consistent JSON error envelope exception handlers
    setup_exception_handlers(app)

    # 3. Mount Prometheus metrics
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # 4. Mount API routers
    # Root level ops endpoints (/health/live, /health/ready)
    app.include_router(ops_router)
    # Versioned API routes (/api/v1/...)
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
