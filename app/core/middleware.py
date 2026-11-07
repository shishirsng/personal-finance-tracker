"""HTTP middlewares for request ID tracking, structured logging, and error envelopes."""
import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger("app.middleware")


class RequestIDAndLoggingMiddleware(BaseHTTPMiddleware):
    """Assigns X-Request-ID, captures request latency, and emits structured logs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()
        response: Response | None = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            user_id = getattr(request.state, "user_id", None)
            
            logger.info(
                "http_request_finished",
                method=request.method,
                path=request.url.path,
                status=status_code,
                latency_ms=latency_ms,
                client_ip=request.client.host if request.client else "unknown",
                user_id=str(user_id) if user_id else None,
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers that output standard error envelopes."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "type": err.get("type"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": errors,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "details": None,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_internal_server_error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                    "details": None,
                }
            },
        )
