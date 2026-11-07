"""Reporting and analytics service with Redis caching."""
import calendar
from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Literal
import uuid
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.repositories.budget_repo import BudgetRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.report import (
    BudgetVsActualItem,
    BudgetVsActualResponse,
    CategoryBreakdownItem,
    CategoryBreakdownResponse,
    MonthlySummaryResponse,
)

settings = get_settings()


class ReportService:
    """Generates monthly financial summaries, category breakdowns, and budget vs actual reports."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.tx_repo = TransactionRepository(session)
        self.budget_repo = BudgetRepository(session)
        self.category_repo = CategoryRepository(session)

    @staticmethod
    def _parse_month(month: str) -> tuple[datetime, datetime]:
        """Convert YYYY-MM into UTC start and end datetimes for query ranges."""
        year, m = map(int, month.split("-"))
        _, last_day = calendar.monthrange(year, m)
        start_dt = datetime(year, m, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(year, m, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return start_dt, end_dt

    async def get_monthly_summary(self, user_id: uuid.UUID, month: str) -> MonthlySummaryResponse:
        """
        Return total income, total expense, net savings, and savings rate.
        Cached in Redis with REPORT_CACHE_TTL_SECONDS. Invalidation occurs on any write affecting user+month.
        """
        cache_key = f"cache:reports:monthly-summary:{user_id}:{month}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return MonthlySummaryResponse(
                    month=data["month"],
                    total_income=Decimal(data["total_income"]),
                    total_expense=Decimal(data["total_expense"]),
                    net_savings=Decimal(data["net_savings"]),
                    savings_rate=Decimal(data["savings_rate"]),
                )
        except Exception:
            pass

        start_dt, end_dt = self._parse_month(month)
        transactions = await self.tx_repo.get_monthly_transactions(user_id, start_dt, end_dt)

        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")

        for tx in transactions:
            if tx.direction == "income":
                total_income += tx.amount
            elif tx.direction == "expense":
                total_expense += tx.amount

        net_savings = total_income - total_expense
        savings_rate = Decimal("0.00")
        if total_income > Decimal("0.00"):
            savings_rate = round((net_savings / total_income) * Decimal("100.00"), 2)

        summary = MonthlySummaryResponse(
            month=month,
            total_income=total_income,
            total_expense=total_expense,
            net_savings=net_savings,
            savings_rate=savings_rate,
        )

        # Write to Redis cache
        cache_data = {
            "month": month,
            "total_income": str(total_income),
            "total_expense": str(total_expense),
            "net_savings": str(net_savings),
            "savings_rate": str(savings_rate),
        }
        try:
            await self.redis.set(cache_key, json.dumps(cache_data), ex=settings.REPORT_CACHE_TTL_SECONDS)
        except Exception:
            pass
        return summary

    async def get_category_breakdown(
        self,
        user_id: uuid.UUID,
        month: str,
        direction: Literal["income", "expense"] = "expense",
    ) -> CategoryBreakdownResponse:
        """Break down expenses or income grouped by category for a month."""
        start_dt, end_dt = self._parse_month(month)
        transactions = await self.tx_repo.get_monthly_transactions(user_id, start_dt, end_dt)

        matching_txs = [t for t in transactions if t.direction == direction]
        total_amount = sum((t.amount for t in matching_txs), Decimal("0.00"))

        grouped: dict[uuid.UUID | None, dict[str, Any]] = {}
        for tx in matching_txs:
            cat_id = tx.category_id
            if cat_id not in grouped:
                cat_name = tx.category.name if tx.category else "Uncategorized"
                grouped[cat_id] = {"name": cat_name, "amount": Decimal("0.00")}
            grouped[cat_id]["amount"] += tx.amount

        items: list[CategoryBreakdownItem] = []
        for cat_id, data in grouped.items():
            amount = data["amount"]
            pct = Decimal("0.00")
            if total_amount > Decimal("0.00"):
                pct = round((amount / total_amount) * Decimal("100.00"), 2)
            items.append(
                CategoryBreakdownItem(
                    category_id=cat_id,
                    category_name=data["name"],
                    total_amount=amount,
                    percentage=pct,
                )
            )

        items.sort(key=lambda x: x.total_amount, reverse=True)
        return CategoryBreakdownResponse(
            month=month,
            direction=direction,
            total_amount=total_amount,
            items=items,
        )

    async def get_budget_vs_actual(self, user_id: uuid.UUID, month: str) -> BudgetVsActualResponse:
        """Compare monthly category budgets with actual expense spending."""
        start_dt, end_dt = self._parse_month(month)
        budgets = await self.budget_repo.list_by_user_and_month(user_id, month)
        transactions = await self.tx_repo.get_monthly_transactions(user_id, start_dt, end_dt)

        actual_expenses: dict[uuid.UUID, Decimal] = {}
        for tx in transactions:
            if tx.direction == "expense" and tx.category_id is not None:
                actual_expenses[tx.category_id] = (
                    actual_expenses.get(tx.category_id, Decimal("0.00")) + tx.amount
                )

        total_budgeted = Decimal("0.00")
        total_actual = Decimal("0.00")
        items: list[BudgetVsActualItem] = []

        seen_categories: set[uuid.UUID] = set()

        for b in budgets:
            seen_categories.add(b.category_id)
            budgeted = b.amount
            actual = actual_expenses.get(b.category_id, Decimal("0.00"))
            difference = budgeted - actual
            pct = Decimal("0.00")
            if budgeted > Decimal("0.00"):
                pct = round((actual / budgeted) * Decimal("100.00"), 2)

            total_budgeted += budgeted
            total_actual += actual
            items.append(
                BudgetVsActualItem(
                    category_id=b.category_id,
                    category_name=b.category.name if b.category else "Unknown",
                    budgeted_amount=budgeted,
                    actual_amount=actual,
                    difference=difference,
                    percentage_used=pct,
                )
            )

        # Include categories that had expenses but no budget defined
        for cat_id, actual in actual_expenses.items():
            if cat_id not in seen_categories:
                category = await self.category_repo.get_by_id_and_user(cat_id, user_id)
                cat_name = category.name if category else "Unbudgeted"
                total_actual += actual
                items.append(
                    BudgetVsActualItem(
                        category_id=cat_id,
                        category_name=cat_name,
                        budgeted_amount=Decimal("0.00"),
                        actual_amount=actual,
                        difference=-actual,
                        percentage_used=Decimal("100.00"),
                    )
                )

        items.sort(key=lambda x: x.actual_amount, reverse=True)
        return BudgetVsActualResponse(
            month=month,
            total_budgeted=total_budgeted,
            total_actual=total_actual,
            items=items,
        )
