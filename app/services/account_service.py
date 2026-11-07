"""Account business logic service."""
from typing import Literal
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundError
from app.models.account import Account
from app.repositories.account_repo import AccountRepository
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.common import PaginatedResponse


class AccountService:
    """Manages financial accounts with strict ownership enforcement."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AccountRepository(session)

    async def create_account(self, user_id: uuid.UUID, payload: AccountCreate) -> AccountResponse:
        """Create a new account owned by user_id."""
        account = Account(
            id=uuid.uuid4(),
            user_id=user_id,
            name=payload.name.strip(),
            type=payload.type,
            currency=payload.currency.upper(),
            is_stale=False,
            last_activity_at=None,
        )
        saved = await self.repo.add(account)
        await self.session.commit()
        return AccountResponse.model_validate(saved)

    async def get_account(self, user_id: uuid.UUID, account_id: uuid.UUID) -> AccountResponse:
        """Fetch account ensuring ownership; return 404 to avoid existence leakage."""
        account = await self.repo.get_by_id_and_user(account_id, user_id)
        if account is None:
            raise EntityNotFoundError(message=f"Account with ID '{account_id}' was not found.")
        return AccountResponse.model_validate(account)

    async def list_accounts(
        self,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        sort_by: Literal["name", "created_at"] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> PaginatedResponse[AccountResponse]:
        """List accounts owned by user with pagination and sorting."""
        accounts, total = await self.repo.list_by_user(
            user_id=user_id,
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = [AccountResponse.model_validate(acc) for acc in accounts]
        next_offset = offset + limit if (offset + limit) < total else None
        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            next_offset=next_offset,
        )

    async def update_account(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        payload: AccountUpdate,
    ) -> AccountResponse:
        """Update account properties."""
        account = await self.repo.get_by_id_and_user(account_id, user_id)
        if account is None:
            raise EntityNotFoundError(message=f"Account with ID '{account_id}' was not found.")

        if payload.name is not None:
            account.name = payload.name.strip()
        if payload.type is not None:
            account.type = payload.type
        if payload.currency is not None:
            account.currency = payload.currency.upper()

        await self.session.commit()
        await self.session.refresh(account)
        return AccountResponse.model_validate(account)

    async def delete_account(self, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
        """Delete account."""
        account = await self.repo.get_by_id_and_user(account_id, user_id)
        if account is None:
            raise EntityNotFoundError(message=f"Account with ID '{account_id}' was not found.")
        await self.session.delete(account)
        await self.session.commit()
