"""FastAPI dependencies for authentication, token extraction, and role authorization."""
from typing import Callable, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.core.jwt import (
    InvalidTokenException,
    TokenExpiredException,
    decode_access_token,
)
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

# Use auto_error=False so we can emit custom 401 JSON responses with codes and WWW-Authenticate
# instead of FastAPI's default 403 Forbidden on missing Authorization headers.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT Bearer token, loading user and location directly from database.

    The user's role and is_active flag are always resolved against the live database record,
    never from token claims. Any account deactivation or role modification takes effect instantly.
    """
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials
    ):
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            code="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    try:
        user_id = decode_access_token(token)
    except TokenExpiredException:
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            code="token_expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenException:
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            code="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(
        select(User)
        .options(joinedload(User.location))
        .where(User.id == user_id)
    )

    if user is None:
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            code="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            code="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Dependency factory enforcing that the authenticated user possesses one of the allowed roles."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AppHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
                code="forbidden",
            )
        return current_user

    return role_checker


# Convenient role enforcement aliases
require_admin = require_role(UserRole.STORE_ADMIN)
require_employee_or_admin = require_role(UserRole.EMPLOYEE, UserRole.STORE_ADMIN)

