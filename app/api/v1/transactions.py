"""Transaction management endpoints with idempotency protection."""
from datetime import datetime
from typing import Literal
import uuid
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.idempotency_service import IdempotencyService
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    account_id: uuid.UUID | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    direction: Literal["income", "expense"] | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sort_by: Literal["occurred_at", "amount"] = Query("occurred_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> PaginatedResponse[TransactionResponse]:
    """Retrieve filtered, paginated transactions for the authenticated user."""
    service = TransactionService(db, redis)
    return await service.list_transactions(
        user_id=current_user.id,
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


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    request: Request,
    payload: TransactionCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Response:
    """
    Log an income or expense transaction.
    Supports Idempotency-Key header: repeated requests return cached response; mismatched bodies return 409 Conflict.
    """
    idempotency_svc = IdempotencyService(redis)
    raw_body = await request.body()
    body_hash = idempotency_svc.hash_payload(raw_body)

    if idempotency_key:
        recorded = await idempotency_svc.get_recorded_response(
            user_id=current_user.id,
            idempotency_key=idempotency_key,
            current_hash=body_hash,
        )
        if recorded is not None:
            return JSONResponse(
                status_code=recorded["status_code"],
                content=recorded["response_body"],
            )

    tx_service = TransactionService(db, redis)
    result = await tx_service.create_transaction(current_user.id, payload)
    response_data = result.model_dump(mode="json")

    if idempotency_key:
        await idempotency_svc.store_response(
            user_id=current_user.id,
            idempotency_key=idempotency_key,
            request_hash=body_hash,
            status_code=status.HTTP_201_CREATED,
            response_body=response_data,
        )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response_data)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TransactionResponse:
    """Retrieve transaction by ID."""
    service = TransactionService(db, redis)
    return await service.get_transaction(current_user.id, transaction_id)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TransactionResponse:
    """Update transaction fields."""
    service = TransactionService(db, redis)
    return await service.update_transaction(current_user.id, transaction_id, payload)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Delete a transaction."""
    service = TransactionService(db, redis)
    await service.delete_transaction(current_user.id, transaction_id)
