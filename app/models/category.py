"""Category domain model."""
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.transaction import Transaction
    from app.models.budget import Budget


class Category(Base, TimestampMixin):
    """Transaction categorization entity."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", "kind", name="uq_user_category_name_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # 'income' | 'expense'
    color: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
    )  # e.g. '#FF5733'

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="category",
    )
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget",
        back_populates="category",
        cascade="all, delete-orphan",
    )
