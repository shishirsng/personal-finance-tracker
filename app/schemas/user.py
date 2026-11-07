"""User schemas."""
from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """User representation response."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Literal["user", "admin"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdateRequest(BaseModel):
    """Admin payload to modify user privileges."""

    role: Literal["user", "admin"] = Field(..., description="New role assigned to user")
