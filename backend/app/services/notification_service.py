"""Service layer for Admin In-App Notifications (Module 9A 4.3)."""
from __future__ import annotations

import math

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.models.inventory_transaction import InventoryTransaction
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import Page
from app.schemas.notification import NotificationItem


def _to_notification_item(notif: Notification) -> NotificationItem:
    """Map Notification ORM to NotificationItem schema."""
    tx = notif.transaction
    part = tx.part if tx else None
    user = tx.user if tx else None

    return NotificationItem(
        id=notif.id,
        message=notif.message,
        is_read=notif.is_read,
        created_at=notif.created_at,
        transaction_id=notif.transaction_id,
        part_id=part.id if part else None,
        part_name=part.name if part else None,
        quantity=abs(tx.quantity_change) if tx else None,
        actor_employee_id=user.employee_id if user else None,
    )


def get_admin_notifications(
    db: Session,
    admin: User,
    notif_status: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> Page[NotificationItem]:
    """Retrieve paginated notifications scoped strictly to the authenticated admin."""
    if notif_status not in {"all", "unread"}:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status filter '{notif_status}'. Must be 'all' or 'unread'",
            code="invalid_status",
            field="status",
        )

    conditions = [Notification.recipient_user_id == admin.id]
    if notif_status == "unread":
        conditions.append(Notification.is_read.is_(False))

    # 1. Total count query (1 constant query)
    count_stmt = select(func.count(Notification.id)).where(*conditions)
    total = db.scalar(count_stmt) or 0

    # 2. Paginated items query with eager transaction, part, and user joins (1 constant query)
    offset = (page - 1) * page_size
    items_stmt = (
        select(Notification)
        .options(
            joinedload(Notification.transaction).joinedload(InventoryTransaction.part),
            joinedload(Notification.transaction).joinedload(InventoryTransaction.user),
        )
        .where(*conditions)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = db.scalars(items_stmt).all()
    items = [_to_notification_item(r) for r in rows]

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    return Page[NotificationItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_unread_count(db: Session, admin: User) -> int:
    """Return count of unread notifications strictly for this admin (1 query)."""
    stmt = select(func.count(Notification.id)).where(
        Notification.recipient_user_id == admin.id,
        Notification.is_read.is_(False),
    )
    return db.scalar(stmt) or 0


def mark_notification_read(
    db: Session,
    admin: User,
    notification_id: int,
) -> NotificationItem:
    """Mark a single notification as read if owned by the admin (404 otherwise)."""
    stmt = (
        select(Notification)
        .options(
            joinedload(Notification.transaction).joinedload(InventoryTransaction.part),
            joinedload(Notification.transaction).joinedload(InventoryTransaction.user),
        )
        .where(
            Notification.id == notification_id,
            Notification.recipient_user_id == admin.id,
        )
    )
    notif = db.scalar(stmt)
    if not notif:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
            code="not_found",
        )

    if not notif.is_read:
        notif.is_read = True
        db.commit()
        db.refresh(notif)

    return _to_notification_item(notif)


def mark_all_read(db: Session, admin: User) -> int:
    """Mark all unread notifications for this admin as read (idempotent)."""
    stmt = (
        update(Notification)
        .where(
            Notification.recipient_user_id == admin.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount

