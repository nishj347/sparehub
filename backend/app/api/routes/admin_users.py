"""Admin endpoints for Employee / User management."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import (
    UserCreate,
    UserPasswordReset,
    UserRead,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Users"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=Page[UserRead])
def list_users(
    q: Optional[str] = Query(None, description="Search by employee ID, name, or email"),
    role: Optional[str] = Query(None, description="Filter by role (EMPLOYEE, STORE_ADMIN)"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    status: str = Query("all", description="Filter by status ('active', 'inactive', 'all')"),
    sort: str = Query("employee_id", description="Sort field ('employee_id', 'name', 'created_at')"),
    order: str = Query("asc", description="Sort order ('asc' or 'desc')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List users with pagination, search, role/location/status filters, and sorting."""
    return user_service.list_users(
        db=db,
        q=q,
        role=role,
        location_id=location_id,
        status_filter=status,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
):
    """Create a new employee or admin user."""
    return user_service.create_user(db=db, data=data)


@router.patch("/{id}", response_model=UserRead)
def update_user(
    id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update employee details. Enforces self-demotion and last-admin protections."""
    return user_service.update_user(
        db=db, user_id=id, data=data, current_user=current_user
    )


@router.post("/{id}/deactivate", response_model=UserRead)
def deactivate_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Deactivate employee account. Admin cannot deactivate themselves or last admin."""
    return user_service.deactivate_user(
        db=db, user_id=id, current_user=current_user
    )


@router.post("/{id}/activate", response_model=UserRead)
def activate_user(
    id: int,
    db: Session = Depends(get_db),
):
    """Activate a deactivated employee account."""
    return user_service.activate_user(db=db, user_id=id)


@router.post("/{id}/reset-password", response_model=UserRead)
def reset_password(
    id: int,
    data: UserPasswordReset,
    db: Session = Depends(get_db),
):
    """Reset user password and unlock account."""
    return user_service.reset_password(db=db, user_id=id, data=data)

