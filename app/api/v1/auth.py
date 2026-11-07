"""Authentication endpoints: register, login, refresh, logout."""
from fastapi import APIRouter, Depends, Form, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_redis, rate_limit_auth
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UserResponse:
    """Register a new user account."""
    service = AuthService(db, redis)
    return await service.register_user(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_auth)],
)
async def login(
    request: Request,
    username: str | None = Form(None),
    password: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """
    Authenticate user and issue JWT access and refresh tokens.
    Supports both standard OAuth2 form-urlencoded and JSON body payloads.
    """
    service = AuthService(db, redis)
    if username is not None and password is not None:
        return await service.authenticate_user(username, password)

    # Try parsing JSON body
    body = await request.json()
    login_data = UserLoginRequest.model_validate(body)
    return await service.authenticate_user(login_data.username, login_data.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """Rotate an unrevoked refresh token to issue a new token pair."""
    service = AuthService(db, redis)
    return await service.refresh_tokens(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Revoke refresh token by adding its JTI to the Redis blocklist."""
    service = AuthService(db, redis)
    await service.revoke_token(payload.refresh_token)
