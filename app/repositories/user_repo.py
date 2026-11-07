"""Repository for User entity."""
from typing import Sequence
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access layer for User accounts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Find user by email address."""
        stmt = select(User).where(User.email == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_users(self) -> int:
        """Count total registered users."""
        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def list_users(self, offset: int = 0, limit: int = 50) -> Sequence[User]:
        """List users paginated ordered by creation time."""
        stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
