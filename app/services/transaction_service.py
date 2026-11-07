"""Transaction business logic service."""
from datetime import datetime
from typing import Literal
import uuid
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundError
from app.models.transaction import Transaction
from app.repositories.account_repo import AccountRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)


class TransactionService:
    """Handles transactions, updates account activity, and invalidates report caches."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.tx_repo = TransactionRepository(session)
        self.account_repo = AccountRepository(session)
        self.category_repo = CategoryRepository(session)

    async def _invalidate_report_cache(self, user_id: uuid.UUID, dt: datetime) -> None:
        """Invalidate the Redis monthly summary cache for this user and month."""
        month_str = dt.strftime("%Y-%m")
        cache_key = f"cache:reports:monthly-summary:{user_id}:{month_str}"
        try:
            await self.redis.delete(cache_key)
        except Exception:
            pass

    async def create_transaction(
        self,
        user_id: uuid.UUID,
        payload: TransactionCreate,
    ) -> TransactionResponse:
        """Create transaction, verify account & category ownership, and touch account last_activity."""
        account = await self.account_repo.get_by_id_and_user(payload.account_id, user_id)
        if account is None:
            raise EntityNotFoundError(message=f"Account with ID '{payload.account_id}' was not found.")

        if payload.category_id is not None:
            category = await self.category_repo.get_by_id_and_user(payload.category_id, user_id)
            if category is None:
                raise EntityNotFoundError(message=f"Category with ID '{payload.category_id}' was not found.")

        # Touch account activity and reset stale flag
        account.last_activity_at = payload.occurred_at
        account.is_stale = False

        tx = Transaction(
            id=uuid.uuid4(),
            account_id=payload.account_id,
            category_id=payload.category_id,
            amount=payload.amount,
            direction=payload.direction,
            description=payload.description.strip() if payload.description else None,
            occurred_at=payload.occurred_at,
        )
        saved = await self.tx_repo.add(tx)
        await self.session.commit()

        # Invalidate affected month's report cache
        await self._invalidate_report_cache(user_id, payload.occurred_at)

        # Re-fetch with loaded category
        full_tx = await self.tx_repo.get_by_id_and_user(saved.id, user_id)
        return TransactionResponse.model_validate(full_tx or saved)

    async def get_transaction(
        self,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> TransactionResponse:
        """Retrieve transaction with ownership check; 404 on foreign resource."""
        tx = await self.tx_repo.get_by_id_and_user(transaction_id, user_id)
        if tx is None:
            raise EntityNotFoundError(message=f"Transaction with ID '{transaction_id}' was not found.")
        return TransactionResponse.model_validate(tx)

    async def list_transactions(
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
    ) -> PaginatedResponse[TransactionResponse]:
        """Fetch filtered, paginated transactions for the authenticated user."""
        transactions, total = await self.tx_repo.list_by_user_with_filters(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            direction=direction,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = [TransactionResponse.model_validate(tx) for tx in transactions]
        next_offset = offset + limit if (offset + limit) < total else None
        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            next_offset=next_offset,
        )

    async def update_transaction(
        self,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        payload: TransactionUpdate,
    ) -> TransactionResponse:
        """Update transaction fields, validating foreign relationships and clearing report cache."""
        tx = await self.tx_repo.get_by_id_and_user(transaction_id, user_id)
        if tx is None:
            raise EntityNotFoundError(message=f"Transaction with ID '{transaction_id}' was not found.")

        old_occurred_at = tx.occurred_at

        if payload.account_id is not None and payload.account_id != tx.account_id:
            account = await self.account_repo.get_by_id_and_user(payload.account_id, user_id)
            if account is None:
                raise EntityNotFoundError(message=f"Account with ID '{payload.account_id}' was not found.")
            tx.account_id = payload.account_id

        if payload.category_id is not None:
            category = await self.category_repo.get_by_id_and_user(payload.category_id, user_id)
            if category is None:
                raise EntityNotFoundError(message=f"Category with ID '{payload.category_id}' was not found.")
            tx.category_id = payload.category_id

        if payload.amount is not None:
            tx.amount = payload.amount
        if payload.direction is not None:
            tx.direction = payload.direction
        if payload.description is not None:
            tx.description = payload.description.strip() if payload.description else None
        if payload.occurred_at is not None:
            tx.occurred_at = payload.occurred_at

        await self.session.commit()

        # Invalidate caches for both old and new dates if month shifted
        await self._invalidate_report_cache(user_id, old_occurred_at)
        if tx.occurred_at.strftime("%Y-%m") != old_occurred_at.strftime("%Y-%m"):
            await self._invalidate_report_cache(user_id, tx.occurred_at)

        full_tx = await self.tx_repo.get_by_id_and_user(transaction_id, user_id)
        return TransactionResponse.model_validate(full_tx or tx)

    async def delete_transaction(self, user_id: uuid.UUID, transaction_id: uuid.UUID) -> None:
        """Delete transaction and invalidate monthly summary cache."""
        tx = await self.tx_repo.get_by_id_and_user(transaction_id, user_id)
        if tx is None:
            raise EntityNotFoundError(message=f"Transaction with ID '{transaction_id}' was not found.")

        occurred_at = tx.occurred_at
        await self.session.delete(tx)
        await self.session.commit()
        await self._invalidate_report_cache(user_id, occurred_at)
