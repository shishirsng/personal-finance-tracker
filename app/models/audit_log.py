"""Audit log model for background tasks and security events."""
from typing import Any
import uuid
from sqlalchemy import JSON, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

# Use PostgreSQL JSONB when available, falling back to JSON on SQLite
JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class AuditLog(Base, TimestampMixin):
    """Audit record capturing asynchronous operations and administrative events."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE,
        nullable=False,
    )
