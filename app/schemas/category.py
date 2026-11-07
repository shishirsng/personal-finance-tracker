"""Category schemas."""
from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field

CategoryKind = Literal["income", "expense"]


class CategoryCreate(BaseModel):
    """Payload for creating a transaction category."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    kind: CategoryKind = Field(..., description="income or expense")
    color: str | None = Field(
        None,
        pattern=r"^#([A-Fa-f0-9]{6})$",
        description="Hex color code (e.g. #FF5733)",
    )


class CategoryUpdate(BaseModel):
    """Payload for modifying an existing category."""

    name: str | None = Field(None, min_length=1, max_length=100)
    kind: CategoryKind | None = None
    color: str | None = Field(None, pattern=r"^#([A-Fa-f0-9]{6})$")


class CategoryResponse(BaseModel):
    """Category response schema."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    kind: CategoryKind
    color: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
