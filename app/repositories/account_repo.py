"""Repository for Account entity."""
from typing import Literal, Sequence
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """Data access layer for financial accounts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Account, session)

    async def get_by_id_and_user(self, account_id: uuid.UUID, user_id: uuid.UUID) -> Account | None:
        """Fetch account ensuring ownership by user_id."""
        stmt = select(Account).where(
            Account.id == account_id,
            Account.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        sort_by: Literal["name", "created_at"] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[Sequence[Account], int]:
        """List and count accounts for a specific user with sorting."""
        count_stmt = select(func.count(Account.id)).where(Account.user_id == user_id)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one() or 0

        sort_col = Account.name if sort_by == "name" else Account.created_at
        order_clause = sort_col.asc() if sort_order == "asc" else sort_col.desc()

        stmt = (
            select(Account)
            .where(Account.user_id == user_id)
            .order_by(order_clause)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total
