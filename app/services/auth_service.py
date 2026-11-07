"""Authentication and token lifecycle service."""
import uuid
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse, UserRegisterRequest
from app.schemas.user import UserResponse

settings = get_settings()


class AuthService:
    """Handles user onboarding, credential verification, and token rotation."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.user_repo = UserRepository(session)

    async def register_user(self, payload: UserRegisterRequest) -> UserResponse:
        """Register a new user account with Argon2 password hashing."""
        existing = await self.user_repo.get_by_email(payload.email)
        if existing is not None:
            raise ConflictError(message=f"An account with email '{payload.email}' already exists.")

        hashed_pw = get_password_hash(payload.password)
        new_user = User(
            id=uuid.uuid4(),
            email=payload.email.lower().strip(),
            password_hash=hashed_pw,
            full_name=payload.full_name.strip(),
            role="user",
        )
        saved_user = await self.user_repo.add(new_user)
        await self.session.commit()
        return UserResponse.model_validate(saved_user)

    async def authenticate_user(self, email: str, password: str) -> TokenResponse:
        """Authenticate credentials and generate access and refresh token pair."""
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError(message="Invalid email or password.")

        access_token = create_access_token(user.id, user.role)
        refresh_token, _, _ = create_refresh_token(user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_tokens(self, refresh_token_str: str) -> TokenResponse:
        """Rotate refresh token and issue new token pair, invalidating old JTI."""
        claims = decode_token(refresh_token_str)
        if claims.get("type") != "refresh":
            raise AuthenticationError(message="Invalid token type: refresh token required.")

        jti = claims.get("jti")
        user_id_str = claims.get("sub")
        if not jti or not user_id_str:
            raise AuthenticationError(message="Malformed token claims.")

        # Check Redis blocklist (fail open in local dev if Redis offline)
        blocklist_key = f"token_blocklist:{jti}"
        try:
            if await self.redis.exists(blocklist_key):
                raise AuthenticationError(message="Refresh token has been revoked.")
        except AuthenticationError:
            raise
        except Exception:
            pass

        user_id = uuid.UUID(user_id_str)
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError(message="User associated with token no longer exists.")

        # Revoke old refresh token JTI in Redis with TTL until its original expiry
        exp = claims.get("exp", 0)
        remaining_ttl = max(int(exp - claims.get("iat", 0)), 3600)
        try:
            await self.redis.set(blocklist_key, "revoked", ex=remaining_ttl)
        except Exception:
            pass

        # Issue fresh rotated pair
        new_access = create_access_token(user.id, user.role)
        new_refresh, _, _ = create_refresh_token(user.id)
        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def revoke_token(self, token_str: str) -> None:
        """Revoke a token by placing its JTI into the Redis blocklist."""
        claims = decode_token(token_str)
        jti = claims.get("jti")
        if not jti:
            return
        exp = claims.get("exp", 0)
        import time
        now = int(time.time())
        ttl = max(exp - now, 3600)
        try:
            await self.redis.set(f"token_blocklist:{jti}", "revoked", ex=ttl)
        except Exception:
            pass
