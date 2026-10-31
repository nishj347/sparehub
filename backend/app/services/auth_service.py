"""Authentication service providing secure credential verification and timing attack protection."""
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User


def authenticate_user(db: Session, identifier: str, password: str) -> User:
    """Authenticate a user by Employee ID (case-insensitive) or Email (case-insensitive).

    Mitigates account enumeration timing attacks via precomputed dummy Argon2 verification.
    Returns 401 with generic message for all failure cases (unknown user, bad password, inactive user).
    Rehashes password if argon2 configuration parameters have changed.
    """
    clean_id = identifier.strip()
    norm_emp_id = clean_id.upper()
    norm_email = clean_id.lower()

    user = db.scalar(
        select(User)
        .options(joinedload(User.location))
        .where(or_(User.employee_id == norm_emp_id, User.email == norm_email))
    )

    if user is None:
        # Mitigate timing attack for non-existent users
        verify_password(password, DUMMY_PASSWORD_HASH)
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            code="invalid_credentials",
        )

    if not user.is_active:
        # Inactive user: verify password to maintain timing consistency, then reject generically
        verify_password(password, user.password_hash)
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            code="invalid_credentials",
        )

    if not verify_password(password, user.password_hash):
        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            code="invalid_credentials",
        )

    # Transparently upgrade password hash if needed
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user

