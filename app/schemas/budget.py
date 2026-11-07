"""Budget schemas."""
from datetime import datetime
from decimal import Decimal
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.category import CategoryResponse


class BudgetUpsert(BaseModel):
    """Payload for creating or updating a category budget for a month."""

    amount: Decimal = Field(..., ge=Decimal("0.00"), decimal_places=2, description="Budgeted target amount")


class BudgetResponse(BaseModel):
    """Budget response schema."""

    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Target month YYYY-MM")
    amount: Decimal
    created_at: datetime
    category: CategoryResponse | None = None

    model_config = ConfigDict(from_attributes=True)
