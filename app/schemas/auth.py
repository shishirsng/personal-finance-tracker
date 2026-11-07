"""Authentication request and response schemas."""
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for registering a new user."""

    email: EmailStr = Field(..., description="User's unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (at least 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name of user")


class UserLoginRequest(BaseModel):
    """Payload for logging in via JSON body."""

    username: EmailStr = Field(..., description="Email address as username")
    password: str = Field(..., description="Plaintext password")


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifespan in seconds")


class RefreshTokenRequest(BaseModel):
    """Payload for refreshing an expired access token."""

    refresh_token: str = Field(..., description="Valid unrevoked refresh token")
