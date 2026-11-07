"""Account management endpoints."""
from typing import Literal
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.common import PaginatedResponse
from app.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sort_by: Literal["name", "created_at"] = Query("created_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AccountResponse]:
    """List all accounts owned by the authenticated user with sorting and pagination."""
    service = AccountService(db)
    return await service.list_accounts(
        user_id=current_user.id,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    """Create a new financial account."""
    service = AccountService(db)
    return await service.create_account(current_user.id, payload)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    """Retrieve an account by ID."""
    service = AccountService(db)
    return await service.get_account(current_user.id, account_id)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    """Update account details."""
    service = AccountService(db)
    return await service.update_account(current_user.id, account_id, payload)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an account."""
    service = AccountService(db)
    await service.delete_account(current_user.id, account_id)
