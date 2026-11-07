"""Account schemas."""
from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field

AccountType = Literal["checking", "savings", "credit", "cash"]


class AccountCreate(BaseModel):
    """Payload for creating a new financial account."""

    name: str = Field(..., min_length=1, max_length=100, description="Display name for account")
    type: AccountType = Field(..., description="Account category type")
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="ISO 4217 three-letter currency code",
    )


class AccountUpdate(BaseModel):
    """Payload for modifying an existing account."""

    name: str | None = Field(None, min_length=1, max_length=100)
    type: AccountType | None = None
    currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")


class AccountResponse(BaseModel):
    """Account response schema."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    type: AccountType
    currency: str
    is_stale: bool
    last_activity_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
