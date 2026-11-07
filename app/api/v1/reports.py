"""Reporting endpoints."""
from typing import Literal
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.report import (
    BudgetVsActualResponse,
    CategoryBreakdownResponse,
    MonthlySummaryResponse,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
async def get_monthly_summary(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Target month YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MonthlySummaryResponse:
    """
    Get aggregated monthly financial summary.
    Cached in Redis; invalidated whenever transactions or budgets for this user+month are mutated.
    """
    service = ReportService(db, redis)
    return await service.get_monthly_summary(current_user.id, month)


@router.get("/category-breakdown", response_model=CategoryBreakdownResponse)
async def get_category_breakdown(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    direction: Literal["income", "expense"] = Query("expense"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> CategoryBreakdownResponse:
    """Get category breakdown for income or expense transactions in a month."""
    service = ReportService(db, redis)
    return await service.get_category_breakdown(current_user.id, month, direction)


@router.get("/budget-vs-actual", response_model=BudgetVsActualResponse)
async def get_budget_vs_actual(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> BudgetVsActualResponse:
    """Compare budgeted limits with actual expenses per category."""
    service = ReportService(db, redis)
    return await service.get_budget_vs_actual(current_user.id, month)
