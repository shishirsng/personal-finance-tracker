"""FastAPI dependency injection providers."""
from collections.abc import AsyncGenerator
import uuid
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.rate_limiter import check_rate_limit
from app.core.redis import get_redis_client
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repo import UserRepository

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield database session per request."""
    async for session in get_db_session():
        yield session


def get_redis() -> Redis:
    """Provide Redis async client dependency."""
    return get_redis_client()


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    Validate JWT access token, check revocation, and resolve user.
    Sets request.state.user_id for structured logging.
    """
    if not token:
        raise AuthenticationError("Authorization header with Bearer token is required.")

    claims = decode_token(token)
    if claims.get("type") != "access":
        raise AuthenticationError("Invalid token type: access token required.")

    jti = claims.get("jti")
    if jti and await redis.exists(f"token_blocklist:{jti}"):
        raise AuthenticationError("Token has been revoked.")

    user_id_str = claims.get("sub")
    if not user_id_str:
        raise AuthenticationError("Invalid token subject.")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as e:
        raise AuthenticationError("Malformed user ID in token.") from e

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found.")

    # Bind user_id to request state for access logging
    request.state.user_id = user.id
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Enforce that current authenticated user holds the 'admin' role."""
    if current_user.role != "admin":
        raise AuthorizationError("Administrator privileges required.")
    return current_user


async def rate_limit_auth(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """Rate limit authentication endpoints to prevent brute-force attacks."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"rate_limit:auth:{client_ip}"
    await check_rate_limit(
        redis=redis,
        key=rate_key,
        max_requests=settings.AUTH_RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )
