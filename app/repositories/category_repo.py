"""Repository for Category entity."""
from typing import Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Data access layer for transaction categories."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Category, session)

    async def get_by_id_and_user(self, category_id: uuid.UUID, user_id: uuid.UUID) -> Category | None:
        """Fetch category ensuring ownership by user_id."""
        stmt = select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        kind: str | None = None,
    ) -> Sequence[Category]:
        """List categories owned by user, optionally filtered by kind."""
        stmt = select(Category).where(Category.user_id == user_id)
        if kind:
            stmt = stmt.where(Category.kind == kind)
        stmt = stmt.order_by(Category.name.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
