"""Custom application exceptions following consistent error envelopes."""
from typing import Any


class AppException(Exception):
    """Base application exception for handled domain and HTTP errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class EntityNotFoundError(AppException):
    """Raised when a requested resource does not exist or user lacks ownership."""

    def __init__(self, message: str = "Resource not found", details: Any = None) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=404,
            details=details,
        )


class AuthenticationError(AppException):
    """Raised on authentication failure or invalid credentials."""

    def __init__(self, message: str = "Authentication failed", details: Any = None) -> None:
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
            details=details,
        )


class AuthorizationError(AppException):
    """Raised when an authenticated user lacks permissions (e.g. non-admin)."""

    def __init__(self, message: str = "Insufficient permissions", details: Any = None) -> None:
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
            details=details,
        )


class ConflictError(AppException):
    """Raised on unique constraint or state conflict."""

    def __init__(self, message: str = "Resource conflict", details: Any = None) -> None:
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
            details=details,
        )


class RateLimitExceededError(AppException):
    """Raised when request rate exceeds allowed threshold."""

    def __init__(self, message: str = "Rate limit exceeded. Try again later.", details: Any = None) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
            details=details,
        )


class BadRequestError(AppException):
    """Raised when request payload or parameters are logically invalid."""

    def __init__(self, message: str = "Invalid request", details: Any = None) -> None:
        super().__init__(
            code="BAD_REQUEST",
            message=message,
            status_code=400,
            details=details,
        )
