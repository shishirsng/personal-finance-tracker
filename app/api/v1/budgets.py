"""Budget management endpoints."""
import uuid
from fastapi import APIRouter, Depends, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.budget import BudgetResponse, BudgetUpsert
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Month formatted as YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> list[BudgetResponse]:
    """Retrieve all category budgets configured for a specific month."""
    service = BudgetService(db, redis)
    budgets = await service.list_budgets(current_user.id, month)
    return list(budgets)


@router.put("/{category_id}", response_model=BudgetResponse)
async def upsert_budget(
    category_id: uuid.UUID,
    payload: BudgetUpsert,
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Month formatted as YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> BudgetResponse:
    """Upsert monthly budget target for a category."""
    service = BudgetService(db, redis)
    return await service.upsert_budget(
        user_id=current_user.id,
        category_id=category_id,
        month=month,
        payload=payload,
    )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Delete a budget entry."""
    service = BudgetService(db, redis)
    await service.delete_budget(current_user.id, budget_id)
