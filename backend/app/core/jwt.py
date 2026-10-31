"""JSON Web Token (JWT) encoding, decoding, and validation utilities."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.core.config import get_settings


class TokenExpiredException(Exception):
    """Raised when an authentication token has expired."""

    pass


class InvalidTokenException(Exception):
    """Raised when an authentication token is malformed, invalid, or missing required claims."""

    pass


def create_access_token(
    user_id: int, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed JWT access token containing only subject (user_id), issued-at, and expiry.

    Note: Sensitive claims, personal identifying information, and user roles are intentionally omitted.
    Roles and status are always resolved directly against the database on each request.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int:
    """Decode and strictly validate a JWT access token, returning the user's integer ID.

    Raises:
        TokenExpiredException: If token exp claim has elapsed.
        InvalidTokenException: If signature fails, payload is malformed, or sub is invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "require": ["sub", "iat", "exp"],
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredException("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenException("Invalid token signature or payload") from exc

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise InvalidTokenException("Token missing valid subject claim")

    try:
        user_id = int(sub)
    except (ValueError, TypeError) as exc:
        raise InvalidTokenException("Token subject must be an integer identifier") from exc

    return user_id

