"""Security utilities for Argon2 password hashing and JWT token handling."""
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
import jwt
from pwdlib import PasswordHash
from app.config import get_settings
from app.core.exceptions import AuthenticationError

settings = get_settings()
_pwd_context = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    """Hash plain password using Argon2id."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """Create a signed JWT access token with user_id and role claims."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str, int]:
    """
    Create a signed JWT refresh token.
    Returns: (token_str, jti_str, expires_in_seconds)
    """
    now = datetime.now(timezone.utc)
    delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = now + delta
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    expires_in_seconds = int(delta.total_seconds())
    return token, jti, expires_in_seconds


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub", "type", "jti"]},
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthenticationError("Invalid token") from e
