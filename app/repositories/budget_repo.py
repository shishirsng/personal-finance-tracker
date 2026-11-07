"""Repository for Budget entity."""
from decimal import Decimal
from typing import Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.budget import Budget
from app.repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    """Data access layer for monthly category budgets."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Budget, session)

    async def get_by_id_and_user(self, budget_id: uuid.UUID, user_id: uuid.UUID) -> Budget | None:
        """Fetch budget by ID ensuring user ownership with category eagerly loaded."""
        stmt = (
            select(Budget)
            .where(Budget.id == budget_id, Budget.user_id == user_id)
            .options(selectinload(Budget.category))  # N+1 avoidance
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_category_and_month(
        self,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        month: str,
    ) -> Budget | None:
        """Fetch budget for specific category and month."""
        stmt = select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == month,
        ).options(selectinload(Budget.category))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user_and_month(
        self,
        user_id: uuid.UUID,
        month: str,
    ) -> Sequence[Budget]:
        """
        List all budgets for a user and month.
        N+1 avoidance: uses selectinload(Budget.category) to fetch all linked categories.
        """
        stmt = (
            select(Budget)
            .where(Budget.user_id == user_id, Budget.month == month)
            .options(selectinload(Budget.category))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(
        self,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        month: str,
        amount: Decimal,
    ) -> Budget:
        """Atomically insert or update budget on conflict of (user_id, category_id, month)."""
        stmt = (
            insert(Budget)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                category_id=category_id,
                month=month,
                amount=amount,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "category_id", "month"],
                set_=dict(amount=amount),
            )
            .returning(Budget)
        )
        result = await self.session.execute(stmt)
        budget = result.scalar_one()
        # Eager load category
        return (await self.get_by_id_and_user(budget.id, user_id)) or budget
