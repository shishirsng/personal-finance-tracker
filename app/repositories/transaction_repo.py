"""Repository for Transaction entity."""
from datetime import datetime
from typing import Literal, Sequence
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.account import Account
from app.models.transaction import Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Data access layer for transactions with eager relationship loading to eliminate N+1 queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Transaction, session)

    async def get_by_id_and_user(self, transaction_id: uuid.UUID, user_id: uuid.UUID) -> Transaction | None:
        """
        Fetch single transaction scoped to user's account.
        N+1 avoidance: uses selectinload(Transaction.category) so serializing category does not trigger extra queries.
        """
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Transaction.id == transaction_id,
                Account.user_id == user_id,
            )
            .options(selectinload(Transaction.category))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user_with_filters(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        direction: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: Literal["occurred_at", "amount"] = "occurred_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[Sequence[Transaction], int]:
        """
        Filter, paginate, and sort transactions belonging to the user.
        N+1 avoidance: uses selectinload(Transaction.category) to batch-fetch all associated categories in a single query.
        """
        base_filter = [Account.user_id == user_id]
        if account_id:
            base_filter.append(Transaction.account_id == account_id)
        if category_id:
            base_filter.append(Transaction.category_id == category_id)
        if direction:
            base_filter.append(Transaction.direction == direction)
        if start_date:
            base_filter.append(Transaction.occurred_at >= start_date)
        if end_date:
            base_filter.append(Transaction.occurred_at <= end_date)

        # Count total
        count_stmt = (
            select(func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .where(*base_filter)
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one() or 0

        # Sort order
        sort_col = Transaction.amount if sort_by == "amount" else Transaction.occurred_at
        order_clause = sort_col.asc() if sort_order == "asc" else sort_col.desc()

        # Query items with eager loading
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(*base_filter)
            .options(selectinload(Transaction.category))  # N+1 prevention
            .order_by(order_clause)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_monthly_transactions(
        self,
        user_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> Sequence[Transaction]:
        """
        Fetch all transactions for a user within a monthly window.
        N+1 avoidance: uses selectinload(Transaction.category) to hydrate categories in one pass for reporting.
        """
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Account.user_id == user_id,
                Transaction.occurred_at >= start_date,
                Transaction.occurred_at <= end_date,
            )
            .options(selectinload(Transaction.category))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
