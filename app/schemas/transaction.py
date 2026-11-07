"""Transaction schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.category import CategoryResponse

Direction = Literal["income", "expense"]


class TransactionCreate(BaseModel):
    """Payload to log a new transaction."""

    account_id: uuid.UUID = Field(..., description="Account this transaction belongs to")
    category_id: uuid.UUID | None = Field(None, description="Optional category assignment")
    amount: Decimal = Field(..., gt=Decimal("0.00"), decimal_places=2, description="Positive transaction amount")
    direction: Direction = Field(..., description="income or expense")
    description: str | None = Field(None, max_length=500, description="Optional memo or description")
    occurred_at: datetime = Field(..., description="Time when transaction occurred (UTC)")


class TransactionUpdate(BaseModel):
    """Payload to update an existing transaction."""

    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    amount: Decimal | None = Field(None, gt=Decimal("0.00"), decimal_places=2)
    direction: Direction | None = None
    description: str | None = Field(None, max_length=500)
    occurred_at: datetime | None = None


class TransactionResponse(BaseModel):
    """Detailed transaction response with nested category when loaded."""

    id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    amount: Decimal
    direction: Direction
    description: str | None
    occurred_at: datetime
    created_at: datetime
    category: CategoryResponse | None = None

    model_config = ConfigDict(from_attributes=True)
