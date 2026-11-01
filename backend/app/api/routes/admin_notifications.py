"""Admin In-App Notifications endpoints (Module 9A 4.3)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.models.user import User
from app.schemas.common import Page
from app.schemas.notification import (
    NotificationItem,
    ReadAllResponse,
    UnreadCountResponse,
)
from app.services.notification_service import (
    get_admin_notifications,
    get_unread_count,
    mark_all_read,
    mark_notification_read,
)

router = APIRouter(
    prefix="/admin/notifications",
    tags=["Admin Notifications"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count for authenticated admin",
)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UnreadCountResponse:
    """Return count of unread notifications for the caller."""
    count = get_unread_count(db=db, admin=current_user)
    return UnreadCountResponse(unread=count)


@router.post(
    "/read-all",
    response_model=ReadAllResponse,
    summary="Mark all unread notifications as read for authenticated admin",
)
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ReadAllResponse:
    """Mark all unread notifications belonging to the caller as read."""
    updated = mark_all_read(db=db, admin=current_user)
    return ReadAllResponse(updated=updated)


@router.get(
    "",
    response_model=Page[NotificationItem],
    summary="List in-app notifications for authenticated admin",
)
def list_notifications(
    status: str = Query("all", description="Filter notifications: 'all' or 'unread'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Page[NotificationItem]:
    """Retrieve paginated notifications newest first."""
    return get_admin_notifications(
        db=db,
        admin=current_user,
        notif_status=status,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{id}/read",
    response_model=NotificationItem,
    summary="Mark a single notification as read",
)
def read_single_notification(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> NotificationItem:
    """Mark notification with id as read. 404 if not found or not owned by caller."""
    return mark_notification_read(db=db, admin=current_user, notification_id=id)

