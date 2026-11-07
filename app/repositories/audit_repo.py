"""Repository for AuditLog entity."""
from typing import Any, Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Data access layer for system audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLog, session)

    async def log_event(self, event_type: str, payload: dict[str, Any]) -> AuditLog:
        """Create a new audit log record."""
        audit = AuditLog(
            id=uuid.uuid4(),
            event_type=event_type,
            payload=payload,
        )
        return await self.add(audit)

    async def list_recent(self, limit: int = 100) -> Sequence[AuditLog]:
        """Fetch most recent audit logs."""
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
