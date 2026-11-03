"""User / Employee administration business logic and database queries."""
import math
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.location import Location
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import (
    UserCreate,
    UserLocationBrief,
    UserPasswordReset,
    UserRead,
    UserUpdate,
)


def escape_like(val: str) -> str:
    """Escape SQL LIKE/ILIKE wildcards in user search queries."""
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _to_user_read(user: User) -> UserRead:
    """Convert User ORM instance to UserRead schema, computing is_locked flag."""
    now = datetime.now(timezone.utc)
    is_locked = bool(user.locked_until and user.locked_until > now)
    return UserRead(
        id=user.id,
        employee_id=user.employee_id,
        name=user.name,
        email=user.email,
        role=user.role,
        location=UserLocationBrief(
            id=user.location.id,
            name=user.location.name,
            code=user.location.code,
        ),
        is_active=user.is_active,
        is_locked=is_locked,
        created_at=user.created_at,
    )


def list_users(
    db: Session,
    q: Optional[str] = None,
    role: Optional[str] = None,
    location_id: Optional[int] = None,
    status_filter: str = "all",
    sort: str = "employee_id",
    order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Page[UserRead]:
    """Retrieve paginated users with filtering and sorting."""
    # Validate status filter
    if status_filter not in ("active", "inactive", "all"):
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status must be one of: 'active', 'inactive', 'all'",
            code="validation_error",
        )

    # Validate sort field
    sort_fields = {
        "employee_id": User.employee_id,
        "name": User.name,
        "created_at": User.created_at,
    }
    if sort not in sort_fields:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Sort field must be one of: {list(sort_fields.keys())}",
            code="validation_error",
        )

    # Build query
    query = select(User).options(joinedload(User.location))

    # Search filter
    if q and q.strip():
        term = f"%{escape_like(q.strip())}%"
        query = query.where(
            or_(
                User.employee_id.ilike(term),
                User.name.ilike(term),
                User.email.ilike(term),
            )
        )

    # Role filter
    if role:
        try:
            role_enum = UserRole(role.upper())
            query = query.where(User.role == role_enum)
        except ValueError:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role '{role}'. Allowed: EMPLOYEE, STORE_ADMIN",
                code="validation_error",
            )

    # Location filter
    if location_id is not None:
        query = query.where(User.location_id == location_id)

    # Status filter
    if status_filter == "active":
        query = query.where(User.is_active == True)
    elif status_filter == "inactive":
        query = query.where(User.is_active == False)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    # Sorting
    sort_col = sort_fields[sort]
    if order.lower() == "desc":
        query = query.order_by(sort_col.desc(), User.id.desc())
    else:
        query = query.order_by(sort_col.asc(), User.id.asc())

    # Pagination
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    items = db.scalars(query).all()
    total_pages = max(1, math.ceil(total / page_size))

    return Page[UserRead](
        items=[_to_user_read(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def create_user(db: Session, data: UserCreate) -> UserRead:
    """Create a new user with hashed password and verification of active location."""
    # Verify active location
    loc = db.scalar(select(Location).where(Location.id == data.location_id))
    if not loc or not loc.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The specified location does not exist or is inactive.",
            code="invalid_location",
            field="location_id",
        )

    # Check duplicate employee_id
    if db.scalar(select(User.id).where(User.employee_id == data.employee_id)):
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An employee with ID '{data.employee_id}' already exists.",
            code="duplicate_employee_id",
            field="employee_id",
        )

    # Check duplicate email
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An employee with email '{data.email}' already exists.",
            code="duplicate_email",
            field="email",
        )

    pw_hash = hash_password(data.password)
    new_user = User(
        employee_id=data.employee_id,
        name=data.name,
        email=data.email,
        password_hash=pw_hash,
        role=data.role,
        location_id=data.location_id,
        is_active=True,
        failed_login_attempts=0,
        locked_until=None,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError as exc:
        db.rollback()
        err_msg = str(exc.orig).lower() if hasattr(exc, "orig") else str(exc).lower()
        if "employee_id" in err_msg:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An employee with ID '{data.employee_id}' already exists.",
                code="duplicate_employee_id",
                field="employee_id",
            )
        if "email" in err_msg:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An employee with email '{data.email}' already exists.",
                code="duplicate_email",
                field="email",
            )
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database integrity conflict occurred while creating user.",
            code="duplicate_conflict",
        )

    # Re-query with location eagerly joined
    user_with_loc = db.scalar(
        select(User).options(joinedload(User.location)).where(User.id == new_user.id)
    )
    return _to_user_read(user_with_loc)


def update_user(db: Session, user_id: int, data: UserUpdate, current_user: User) -> UserRead:
    """Update employee details. Enforces self-action and last-admin protections on demotion."""
    user = db.scalar(
        select(User).options(joinedload(User.location)).where(User.id == user_id)
    )
    if not user:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
            code="user_not_found",
        )

    # Role change checks
    if data.role is not None and data.role != user.role:
        if user.role == UserRole.STORE_ADMIN and data.role != UserRole.STORE_ADMIN:
            # Cannot demote self
            if current_user.id == user.id:
                raise AppHTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Administrators cannot demote their own account.",
                    code="self_action_forbidden",
                )
            # Cannot demote last active admin
            active_admin_count = db.scalar(
                select(func.count(User.id)).where(
                    User.role == UserRole.STORE_ADMIN, User.is_active == True
                )
            ) or 0
            if user.is_active and active_admin_count <= 1:
                raise AppHTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot demote the last active Store Administrator.",
                    code="last_admin",
                )
        user.role = data.role

    # Email update check
    if data.email is not None and data.email != user.email:
        conflict = db.scalar(
            select(User.id).where(User.email == data.email, User.id != user.id)
        )
        if conflict:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An employee with email '{data.email}' already exists.",
                code="duplicate_email",
                field="email",
            )
        user.email = data.email

    # Name update
    if data.name is not None:
        user.name = data.name

    # Location update check
    if data.location_id is not None and data.location_id != user.location_id:
        loc = db.scalar(select(Location).where(Location.id == data.location_id))
        if not loc or not loc.is_active:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The specified location does not exist or is inactive.",
                code="invalid_location",
                field="location_id",
            )
        user.location_id = data.location_id

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        err_msg = str(exc.orig).lower() if hasattr(exc, "orig") else str(exc).lower()
        if "email" in err_msg:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An employee with email '{data.email}' already exists.",
                code="duplicate_email",
                field="email",
            )
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database integrity conflict occurred while updating user.",
            code="duplicate_conflict",
        )

    # Re-fetch with joined location
    user_with_loc = db.scalar(
        select(User).options(joinedload(User.location)).where(User.id == user.id)
    )
    return _to_user_read(user_with_loc)


def deactivate_user(db: Session, user_id: int, current_user: User) -> UserRead:
    """Deactivate user account. Prevents self-deactivation and deactivating the last active admin."""
    user = db.scalar(
        select(User).options(joinedload(User.location)).where(User.id == user_id)
    )
    if not user:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
            code="user_not_found",
        )

    if current_user.id == user.id:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Administrators cannot deactivate their own account.",
            code="self_action_forbidden",
        )

    if user.is_active and user.role == UserRole.STORE_ADMIN:
        active_admin_count = db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.STORE_ADMIN, User.is_active == True
            )
        ) or 0
        if active_admin_count <= 1:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot deactivate the last active Store Administrator.",
                code="last_admin",
            )

    user.is_active = False
    db.commit()
    db.refresh(user)
    return _to_user_read(user)


def activate_user(db: Session, user_id: int) -> UserRead:
    """Activate a user account."""
    user = db.scalar(
        select(User).options(joinedload(User.location)).where(User.id == user_id)
    )
    if not user:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
            code="user_not_found",
        )

    user.is_active = True
    db.commit()
    db.refresh(user)
    return _to_user_read(user)


def reset_password(db: Session, user_id: int, data: UserPasswordReset) -> UserRead:
    """Reset user password, clearing failed login attempts and unlocking account."""
    user = db.scalar(
        select(User).options(joinedload(User.location)).where(User.id == user_id)
    )
    if not user:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
            code="user_not_found",
        )

    user.password_hash = hash_password(data.password)
    user.failed_login_attempts = 0
    user.locked_until = None

    db.commit()
    db.refresh(user)
    return _to_user_read(user)

