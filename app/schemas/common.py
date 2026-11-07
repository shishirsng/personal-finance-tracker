"""Common Pydantic models for pagination and standardized error envelopes."""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized offset-based paginated response envelope."""

    items: list[T]
    total: int = Field(..., ge=0, description="Total number of items matching filter")
    limit: int = Field(..., ge=1, description="Page limit applied to request")
    offset: int = Field(..., ge=0, description="Page offset applied to request")
    next_offset: int | None = Field(None, description="Offset for next page, or null if on last page")


class ErrorDetails(BaseModel):
    """Detailed error object within error envelope."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Any = Field(None, description="Optional granular diagnostics, e.g. validation errors")


class ErrorEnvelope(BaseModel):
    """Standard top-level error response envelope."""

    error: ErrorDetails
