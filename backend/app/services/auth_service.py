"""Authentication service providing secure credential verification, lockout, and timing attack protection."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.config import get_settings
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
    Enforces account lockout on repeated failed attempts (Module 11A).
    Returns 401 with generic message for all failure cases (unknown user, bad password, inactive user).
    Returns 429 when account is locked.
    Rehashes password if argon2 configuration parameters have changed.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

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

    # Check Account Lockout BEFORE verifying password
    if user.locked_until and user.locked_until > now:
        remaining_sec = max(1, int((user.locked_until - now).total_seconds()))
        raise AppHTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
            code="too_many_attempts",
            headers={"Retry-After": str(remaining_sec)},
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
        # Atomic increment of failed login attempts
        res = db.execute(
            text(
                "UPDATE users SET failed_login_attempts = failed_login_attempts + 1 "
                "WHERE id = :uid RETURNING failed_login_attempts"
            ),
            {"uid": user.id},
        ).scalar()

        if res is not None and res >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
            db.execute(
                text("UPDATE users SET locked_until = :locked_until WHERE id = :uid"),
                {"locked_until": locked_until, "uid": user.id},
            )

        db.commit()

        raise AppHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            code="invalid_credentials",
        )

    # Password verified successfully — reset failed attempts and unlock
    if user.failed_login_attempts > 0 or user.locked_until is not None:
        db.execute(
            text("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = :uid"),
            {"uid": user.id},
        )
        db.commit()
        db.refresh(user)

    # Transparently upgrade password hash if needed
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
