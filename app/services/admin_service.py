"""Admin operations service."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundError
from app.repositories.user_repo import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserResponse


class AdminService:
    """Administrative management of users and permissions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def list_users(self, offset: int = 0, limit: int = 50) -> PaginatedResponse[UserResponse]:
        """List all registered users with offset pagination."""
        total = await self.user_repo.count_users()
        users = await self.user_repo.list_users(offset=offset, limit=limit)
        items = [UserResponse.model_validate(u) for u in users]
        next_offset = offset + limit if (offset + limit) < total else None
        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            next_offset=next_offset,
        )

    async def update_user_role(self, target_user_id: uuid.UUID, new_role: str) -> UserResponse:
        """Modify role for a user."""
        user = await self.user_repo.get_by_id(target_user_id)
        if user is None:
            raise EntityNotFoundError(message=f"User with ID '{target_user_id}' was not found.")

        user.role = new_role
        await self.session.commit()
        await self.session.refresh(user)
        return UserResponse.model_validate(user)
