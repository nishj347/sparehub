"""Service layer for Employee Issue History and Admin Inventory Activity Ledger."""
from __future__ import annotations

import math
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.core.storage import storage_service
from app.models.enums import TransactionType
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.spare_part import SparePart
from app.models.user import User
from app.schemas.activity import (
    ActivityActor,
    AdminActivityItem,
    AdminActivityLocationBrief,
    AdminActivityPartBrief,
    AdminActivityResponse,
    AdminActivitySummary,
    IssueSummary,
    MyIssueItem,
    MyIssueLocationBrief,
    MyIssuePartBrief,
    MyIssuesResponse,
)


def escape_like(val: str) -> str:
    """Escape SQL LIKE/ILIKE wildcards in user search queries."""
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_my_issues(
    db: Session,
    current_user: User,
    q: Optional[str] = None,
    location_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> MyIssuesResponse:
    """Retrieve paginated issue history strictly for the authenticated caller (Module 9A 4.1)."""
    # 1. Validation
    if date_from and date_to and date_from > date_to:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from cannot be after date_to",
            code="invalid_date_range",
            field="date_from",
        )

    valid_sorts = {"created_at", "part_name", "quantity"}
    if sort not in valid_sorts:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort field '{sort}'. Must be one of: {', '.join(sorted(valid_sorts))}",
            code="invalid_sort",
            field="sort",
        )

    if order.lower() not in {"asc", "desc"}:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order must be 'asc' or 'desc'",
            code="invalid_order",
            field="order",
        )

    # 2. Base conditions: strictly for this user and type = ISSUED
    conditions = [
        InventoryTransaction.user_id == current_user.id,
        InventoryTransaction.transaction_type == TransactionType.ISSUED,
    ]

    if location_id is not None:
        conditions.append(InventoryTransaction.location_id == location_id)

    if date_from is not None:
        dt_from = datetime.combine(date_from, time.min).replace(tzinfo=timezone.utc)
        conditions.append(InventoryTransaction.created_at >= dt_from)

    if date_to is not None:
        dt_to = datetime.combine(date_to, time.max).replace(tzinfo=timezone.utc)
        conditions.append(InventoryTransaction.created_at <= dt_to)

    if q and q.strip():
        term = f"%{escape_like(q.strip())}%"
        conditions.append(
            or_(
                SparePart.name.ilike(term),
                SparePart.part_number.ilike(term),
            )
        )

    # 3. Query 1 (Constant count/aggregate query)
    summary_stmt = (
        select(
            func.count(InventoryTransaction.id),
            func.coalesce(func.sum(-InventoryTransaction.quantity_change), 0),
        )
        .join(SparePart, InventoryTransaction.part_id == SparePart.id)
        .where(*conditions)
    )
    total_issues, total_units = db.execute(summary_stmt).one()

    # 4. Sorting setup
    is_desc = order.lower() == "desc"
    if sort == "created_at":
        sort_col = InventoryTransaction.created_at.desc() if is_desc else InventoryTransaction.created_at.asc()
    elif sort == "part_name":
        sort_col = SparePart.name.desc() if is_desc else SparePart.name.asc()
    else:  # quantity
        qty_expr = func.abs(InventoryTransaction.quantity_change)
        sort_col = qty_expr.desc() if is_desc else qty_expr.asc()

    order_criteria = [sort_col, InventoryTransaction.id.desc()]

    # 5. Query 2 (Constant items query with joinedload)
    offset = (page - 1) * page_size
    items_stmt = (
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.part),
            joinedload(InventoryTransaction.location),
        )
        .join(SparePart, InventoryTransaction.part_id == SparePart.id)
        .where(*conditions)
        .order_by(*order_criteria)
        .offset(offset)
        .limit(page_size)
    )
    tx_rows = db.scalars(items_stmt).all()

    items = [
        MyIssueItem(
            transaction_id=tx.id,
            created_at=tx.created_at,
            part=MyIssuePartBrief(
                id=tx.part.id,
                part_number=tx.part.part_number,
                name=tx.part.name,
                image_url=storage_service.public_url(tx.part.image_path)
                if tx.part.image_path
                else None,
            ),
            quantity=abs(tx.quantity_change),
            location=MyIssueLocationBrief(
                id=tx.location.id,
                name=tx.location.name,
                code=tx.location.code,
            ),
            notes=tx.notes,
        )
        for tx in tx_rows
    ]

    total_pages = max(1, math.ceil(total_issues / page_size)) if total_issues > 0 else 1

    return MyIssuesResponse(
        items=items,
        total=total_issues,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        summary=IssueSummary(total_issues=total_issues, total_units=int(total_units)),
    )


def get_admin_activity(
    db: Session,
    q: Optional[str] = None,
    employee: Optional[str] = None,
    tx_type: Optional[str] = None,
    location_id: Optional[int] = None,
    part_id: Optional[int] = None,
    user_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> AdminActivityResponse:
    """Retrieve paginated full inventory activity ledger for Store Admin (Module 9A 4.2)."""
    # 1. Validation
    if date_from and date_to and date_from > date_to:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from cannot be after date_to",
            code="invalid_date_range",
            field="date_from",
        )

    valid_sorts = {"created_at", "part_name", "quantity", "type"}
    if sort not in valid_sorts:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort field '{sort}'. Must be one of: {', '.join(sorted(valid_sorts))}",
            code="invalid_sort",
            field="sort",
        )

    if order.lower() not in {"asc", "desc"}:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order must be 'asc' or 'desc'",
            code="invalid_order",
            field="order",
        )

    conditions = []

    if tx_type and tx_type.lower() != "all":
        try:
            enum_type = TransactionType(tx_type.upper())
            conditions.append(InventoryTransaction.transaction_type == enum_type)
        except ValueError:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid transaction type '{tx_type}'. Must be one of: ISSUED, RECEIVED, ADJUSTED, all",
                code="invalid_type",
                field="type",
            )

    if location_id is not None:
        conditions.append(InventoryTransaction.location_id == location_id)

    if part_id is not None:
        conditions.append(InventoryTransaction.part_id == part_id)

    if user_id is not None:
        conditions.append(InventoryTransaction.user_id == user_id)

    if date_from is not None:
        dt_from = datetime.combine(date_from, time.min).replace(tzinfo=timezone.utc)
        conditions.append(InventoryTransaction.created_at >= dt_from)

    if date_to is not None:
        dt_to = datetime.combine(date_to, time.max).replace(tzinfo=timezone.utc)
        conditions.append(InventoryTransaction.created_at <= dt_to)

    if q and q.strip():
        term = f"%{escape_like(q.strip())}%"
        conditions.append(
            or_(
                SparePart.name.ilike(term),
                SparePart.part_number.ilike(term),
            )
        )

    if employee and employee.strip():
        emp_term = f"%{escape_like(employee.strip())}%"
        conditions.append(
            or_(
                User.name.ilike(emp_term),
                User.employee_id.ilike(emp_term),
            )
        )

    # 2. Query 1 (Summary aggregates in 1 constant query)
    issued_case = case(
        (InventoryTransaction.transaction_type == TransactionType.ISSUED, -InventoryTransaction.quantity_change),
        else_=0,
    )
    received_case = case(
        (InventoryTransaction.transaction_type == TransactionType.RECEIVED, InventoryTransaction.quantity_change),
        else_=0,
    )

    summary_stmt = (
        select(
            func.count(InventoryTransaction.id),
            func.coalesce(func.sum(issued_case), 0),
            func.coalesce(func.sum(received_case), 0),
        )
        .join(SparePart, InventoryTransaction.part_id == SparePart.id)
        .outerjoin(User, InventoryTransaction.user_id == User.id)
        .where(*conditions)
    )
    total_rows, units_issued, units_received = db.execute(summary_stmt).one()

    # 3. Sorting setup
    is_desc = order.lower() == "desc"
    if sort == "created_at":
        sort_col = InventoryTransaction.created_at.desc() if is_desc else InventoryTransaction.created_at.asc()
    elif sort == "part_name":
        sort_col = SparePart.name.desc() if is_desc else SparePart.name.asc()
    elif sort == "type":
        sort_col = InventoryTransaction.transaction_type.desc() if is_desc else InventoryTransaction.transaction_type.asc()
    else:  # quantity
        qty_expr = func.abs(InventoryTransaction.quantity_change)
        sort_col = qty_expr.desc() if is_desc else qty_expr.asc()

    order_criteria = [sort_col, InventoryTransaction.id.desc()]

    # 4. Query 2 (Paginated rows with joinedload)
    offset = (page - 1) * page_size
    items_stmt = (
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.part),
            joinedload(InventoryTransaction.location),
            joinedload(InventoryTransaction.user),
        )
        .join(SparePart, InventoryTransaction.part_id == SparePart.id)
        .outerjoin(User, InventoryTransaction.user_id == User.id)
        .where(*conditions)
        .order_by(*order_criteria)
        .offset(offset)
        .limit(page_size)
    )
    tx_rows = db.scalars(items_stmt).all()

    items = [
        AdminActivityItem(
            id=tx.id,
            created_at=tx.created_at,
            type=tx.transaction_type.value,
            quantity_change=tx.quantity_change,
            quantity_after=tx.quantity_after,
            part=AdminActivityPartBrief(
                id=tx.part.id,
                part_number=tx.part.part_number,
                name=tx.part.name,
            ),
            location=AdminActivityLocationBrief(
                id=tx.location.id,
                name=tx.location.name,
                code=tx.location.code,
            ),
            actor=ActivityActor(
                user_id=tx.user.id,
                employee_id=tx.user.employee_id,
                name=tx.user.name,
                role=tx.user.role.value,
            )
            if tx.user
            else None,
            notes=tx.notes,
        )
        for tx in tx_rows
    ]

    total_pages = max(1, math.ceil(total_rows / page_size)) if total_rows > 0 else 1

    return AdminActivityResponse(
        items=items,
        total=total_rows,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        summary=AdminActivitySummary(
            total_rows=total_rows,
            units_issued=int(units_issued),
            units_received=int(units_received),
        ),
    )

