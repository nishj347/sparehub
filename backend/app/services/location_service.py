"""Location master data business logic and database queries."""
import math
from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from app.core.exceptions import AppHTTPException
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.machine import Machine
from app.models.user import User
from app.schemas.common import Page
from app.schemas.location import LocationCreate, LocationOption, LocationRead, LocationUpdate


def escape_like(val: str) -> str:
    """Escape SQL LIKE/ILIKE wildcards in user search queries."""
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _get_location_counts_subqueries():
    """Return correlated scalar subqueries for location aggregate counts."""
    user_cnt = (
        select(func.count(User.id))
        .where(User.location_id == Location.id)
        .scalar_subquery()
    )
    machine_cnt = (
        select(func.count(Machine.id))
        .where(Machine.location_id == Location.id)
        .scalar_subquery()
    )
    stocked_cnt = (
        select(func.count(Inventory.id))
        .where(Inventory.location_id == Location.id, Inventory.quantity > 0)
        .scalar_subquery()
    )
    return user_cnt, machine_cnt, stocked_cnt


def list_locations(
    db: Session,
    q: Optional[str] = None,
    status_filter: str = "all",
    sort: str = "name",
    order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Page[LocationRead]:
    """Retrieve paginated locations with aggregate counts in a single query (no N+1)."""
    # Validate status filter
    if status_filter not in ("active", "inactive", "all"):
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status must be one of: 'active', 'inactive', 'all'",
            code="validation_error",
        )

    # Validate sorting column
    sort_fields = {
        "name": Location.name,
        "code": Location.code,
        "city": Location.city,
        "created_at": Location.created_at,
    }
    if sort not in sort_fields:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort parameter. Allowed options: {', '.join(sort_fields.keys())}",
            code="validation_error",
        )

    # Validate order
    if order not in ("asc", "desc"):
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order must be 'asc' or 'desc'",
            code="validation_error",
        )

    # Build filtering conditions
    conditions = []
    if status_filter == "active":
        conditions.append(Location.is_active.is_(True))
    elif status_filter == "inactive":
        conditions.append(Location.is_active.is_(False))

    if q and q.strip():
        search_pattern = f"%{escape_like(q.strip())}%"
        conditions.append(
            or_(
                Location.name.ilike(search_pattern),
                Location.code.ilike(search_pattern),
                Location.city.ilike(search_pattern),
            )
        )

    # Count matching records
    count_stmt = select(func.count(Location.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = db.scalar(count_stmt) or 0

    # Build primary query with aggregate counts subqueries
    user_cnt, machine_cnt, stocked_cnt = _get_location_counts_subqueries()
    stmt = select(
        Location,
        user_cnt.label("user_count"),
        machine_cnt.label("machine_count"),
        stocked_cnt.label("stocked_part_count"),
    )
    if conditions:
        stmt = stmt.where(*conditions)

    # Apply sorting with deterministic secondary sort on ID
    sort_col = sort_fields[sort]
    if order == "desc":
        stmt = stmt.order_by(sort_col.desc(), Location.id.desc())
    else:
        stmt = stmt.order_by(sort_col.asc(), Location.id.asc())

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    rows = db.execute(stmt).all()
    items = [
        LocationRead(
            id=loc.id,
            name=loc.name,
            code=loc.code,
            city=loc.city,
            is_active=loc.is_active,
            created_at=loc.created_at,
            user_count=u_count or 0,
            machine_count=m_count or 0,
            stocked_part_count=s_count or 0,
        )
        for loc, u_count, m_count, s_count in rows
    ]

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return Page(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


def get_location_options(db: Session) -> List[LocationOption]:
    """Return active locations sorted alphabetically for dropdown selection menus."""
    stmt = (
        select(Location)
        .where(Location.is_active.is_(True))
        .order_by(Location.name.asc())
    )
    locations = db.scalars(stmt).all()
    return [LocationOption.model_validate(loc) for loc in locations]


def get_location_by_id(db: Session, location_id: int) -> LocationRead:
    """Retrieve a single location with its aggregate metrics, raising 404 if not found."""
    user_cnt, machine_cnt, stocked_cnt = _get_location_counts_subqueries()
    stmt = (
        select(
            Location,
            user_cnt.label("user_count"),
            machine_cnt.label("machine_count"),
            stocked_cnt.label("stocked_part_count"),
        )
        .where(Location.id == location_id)
    )
    row = db.execute(stmt).first()
    if not row:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found",
            code="not_found",
        )

    loc, u_count, m_count, s_count = row
    return LocationRead(
        id=loc.id,
        name=loc.name,
        code=loc.code,
        city=loc.city,
        is_active=loc.is_active,
        created_at=loc.created_at,
        user_count=u_count or 0,
        machine_count=m_count or 0,
        stocked_part_count=s_count or 0,
    )


def create_location(db: Session, data: LocationCreate) -> LocationRead:
    """Create a new location, checking uniqueness for name and code."""
    # Case-insensitive name uniqueness check
    existing_name = db.scalar(
        select(Location).where(func.lower(Location.name) == data.name.lower())
    )
    if existing_name:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location with name '{data.name}' already exists",
            code="duplicate_name",
            field="name",
        )

    # Unique code check (case-insensitive)
    existing_code = db.scalar(
        select(Location).where(func.lower(Location.code) == data.code.lower())
    )
    if existing_code:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location with code '{data.code}' already exists",
            code="duplicate_code",
            field="code",
        )

    new_loc = Location(
        name=data.name,
        code=data.code,
        city=data.city,
        is_active=True,
    )
    db.add(new_loc)
    try:
        db.commit()
        db.refresh(new_loc)
    except IntegrityError as exc:
        db.rollback()
        err_msg = str(getattr(exc, "orig", exc)).lower()
        if "code" in err_msg or "uq_locations_code" in err_msg:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location with code '{data.code}' already exists",
                code="duplicate_code",
                field="code",
            )
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location with name '{data.name}' already exists",
            code="duplicate_name",
            field="name",
        )

    return get_location_by_id(db, new_loc.id)


def update_location(
    db: Session, location_id: int, data: LocationUpdate
) -> LocationRead:
    """Update fields on an existing location."""
    # Verify that at least one field is provided
    if not data.model_fields_set:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be provided for update",
            code="empty_update",
        )

    loc = db.scalar(select(Location).where(Location.id == location_id))
    if not loc:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found",
            code="not_found",
        )

    # Check name uniqueness if updated
    if data.name is not None and data.name.lower() != loc.name.lower():
        existing_name = db.scalar(
            select(Location).where(
                func.lower(Location.name) == data.name.lower(),
                Location.id != location_id,
            )
        )
        if existing_name:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location with name '{data.name}' already exists",
                code="duplicate_name",
                field="name",
            )
        loc.name = data.name

    # Check code uniqueness if updated
    if data.code is not None and data.code.lower() != loc.code.lower():
        existing_code = db.scalar(
            select(Location).where(
                func.lower(Location.code) == data.code.lower(),
                Location.id != location_id,
            )
        )
        if existing_code:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location with code '{data.code}' already exists",
                code="duplicate_code",
                field="code",
            )
        loc.code = data.code

    if data.city is not None:
        loc.city = data.city

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        err_msg = str(getattr(exc, "orig", exc)).lower()
        if "code" in err_msg or "uq_locations_code" in err_msg:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Location code already exists",
                code="duplicate_code",
                field="code",
            )
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location name already exists",
            code="duplicate_name",
            field="name",
        )

    return get_location_by_id(db, location_id)


def deactivate_location(db: Session, location_id: int) -> LocationRead:
    """Soft deactivate a location if not blocked by active users or stocked parts."""
    loc = db.scalar(select(Location).where(Location.id == location_id))
    if not loc:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found",
            code="not_found",
        )

    # Idempotent return if already inactive
    if not loc.is_active:
        return get_location_by_id(db, location_id)

    # Guard: Block if active users or positive inventory exist
    active_users = db.scalar(
        select(func.count(User.id)).where(
            User.location_id == location_id,
            User.is_active.is_(True),
        )
    ) or 0

    stocked_parts = db.scalar(
        select(func.count(Inventory.id)).where(
            Inventory.location_id == location_id,
            Inventory.quantity > 0,
        )
    ) or 0

    if active_users > 0 or stocked_parts > 0:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot deactivate: {active_users} active user(s) and {stocked_parts} stocked part(s) are assigned to this location.",
            code="location_in_use",
        )

    loc.is_active = False
    db.commit()
    return get_location_by_id(db, location_id)


def activate_location(db: Session, location_id: int) -> LocationRead:
    """Reactivate an inactive location."""
    loc = db.scalar(select(Location).where(Location.id == location_id))
    if not loc:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found",
            code="not_found",
        )

    if loc.is_active:
        return get_location_by_id(db, location_id)

    loc.is_active = True
    db.commit()
    return get_location_by_id(db, location_id)
