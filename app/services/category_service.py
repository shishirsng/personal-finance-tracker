"""Category business logic service."""
from typing import Sequence
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ConflictError, EntityNotFoundError
from app.models.category import Category
from app.repositories.category_repo import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate


class CategoryService:
    """Manages categories with ownership validation and unique constraint handling."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CategoryRepository(session)

    async def create_category(self, user_id: uuid.UUID, payload: CategoryCreate) -> CategoryResponse:
        """Create category owned by user."""
        existing = await self.repo.list_by_user(user_id=user_id, kind=payload.kind)
        if any(c.name.lower() == payload.name.strip().lower() for c in existing):
            raise ConflictError(
                message=f"Category '{payload.name}' of kind '{payload.kind}' already exists."
            )

        category = Category(
            id=uuid.uuid4(),
            user_id=user_id,
            name=payload.name.strip(),
            kind=payload.kind,
            color=payload.color.upper() if payload.color else None,
        )
        saved = await self.repo.add(category)
        await self.session.commit()
        return CategoryResponse.model_validate(saved)

    async def get_category(self, user_id: uuid.UUID, category_id: uuid.UUID) -> CategoryResponse:
        """Fetch category with ownership check; 404 on foreign category."""
        category = await self.repo.get_by_id_and_user(category_id, user_id)
        if category is None:
            raise EntityNotFoundError(message=f"Category with ID '{category_id}' was not found.")
        return CategoryResponse.model_validate(category)

    async def list_categories(
        self,
        user_id: uuid.UUID,
        kind: str | None = None,
    ) -> Sequence[CategoryResponse]:
        """List all categories for user, optionally filtered by kind."""
        categories = await self.repo.list_by_user(user_id=user_id, kind=kind)
        return [CategoryResponse.model_validate(c) for c in categories]

    async def update_category(
        self,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        payload: CategoryUpdate,
    ) -> CategoryResponse:
        """Update category fields."""
        category = await self.repo.get_by_id_and_user(category_id, user_id)
        if category is None:
            raise EntityNotFoundError(message=f"Category with ID '{category_id}' was not found.")

        if payload.name is not None:
            category.name = payload.name.strip()
        if payload.kind is not None:
            category.kind = payload.kind
        if payload.color is not None:
            category.color = payload.color.upper() if payload.color else None

        await self.session.commit()
        await self.session.refresh(category)
        return CategoryResponse.model_validate(category)

    async def delete_category(self, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
        """Delete category."""
        category = await self.repo.get_by_id_and_user(category_id, user_id)
        if category is None:
            raise EntityNotFoundError(message=f"Category with ID '{category_id}' was not found.")
        await self.session.delete(category)
        await self.session.commit()
