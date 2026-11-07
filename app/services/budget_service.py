"""Budget business logic service."""
from typing import Sequence
import uuid
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundError
from app.repositories.budget_repo import BudgetRepository
from app.repositories.category_repo import CategoryRepository
from app.schemas.budget import BudgetResponse, BudgetUpsert


class BudgetService:
    """Manages monthly category budgets and cache invalidations."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.budget_repo = BudgetRepository(session)
        self.category_repo = CategoryRepository(session)

    async def _invalidate_report_cache(self, user_id: uuid.UUID, month: str) -> None:
        cache_key = f"cache:reports:monthly-summary:{user_id}:{month}"
        try:
            await self.redis.delete(cache_key)
        except Exception:
            pass

    async def upsert_budget(
        self,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        month: str,
        payload: BudgetUpsert,
    ) -> BudgetResponse:
        """Upsert budget target for user, category, and month."""
        category = await self.category_repo.get_by_id_and_user(category_id, user_id)
        if category is None:
            raise EntityNotFoundError(message=f"Category with ID '{category_id}' was not found.")

        budget = await self.budget_repo.upsert(
            user_id=user_id,
            category_id=category_id,
            month=month,
            amount=payload.amount,
        )
        await self.session.commit()
        await self._invalidate_report_cache(user_id, month)
        return BudgetResponse.model_validate(budget)

    async def list_budgets(self, user_id: uuid.UUID, month: str) -> Sequence[BudgetResponse]:
        """Fetch all category budgets for a user in a given month."""
        budgets = await self.budget_repo.list_by_user_and_month(user_id, month)
        return [BudgetResponse.model_validate(b) for b in budgets]

    async def delete_budget(self, user_id: uuid.UUID, budget_id: uuid.UUID) -> None:
        """Delete budget and invalidate monthly report cache."""
        budget = await self.budget_repo.get_by_id_and_user(budget_id, user_id)
        if budget is None:
            raise EntityNotFoundError(message=f"Budget with ID '{budget_id}' was not found.")

        month = budget.month
        await self.session.delete(budget)
        await self.session.commit()
        await self._invalidate_report_cache(user_id, month)
