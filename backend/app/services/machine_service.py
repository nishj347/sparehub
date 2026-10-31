"""Machine master data business logic and database queries."""
import math
from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.models.location import Location
from app.models.machine import Machine
from app.models.part_machine import PartMachine
from app.schemas.common import Page
from app.schemas.machine import (
    LocationBrief,
    MachineCreate,
    MachineOption,
    MachineRead,
    MachineUpdate,
)
from app.services.location_service import escape_like


def _get_part_count_subquery():
    """Return correlated scalar subquery for machine linked spare part count."""
    return (
        select(func.count(PartMachine.part_id))
        .where(PartMachine.machine_id == Machine.id)
        .scalar_subquery()
    )


def list_machines(
    db: Session,
    q: Optional[str] = None,
    status_filter: str = "all",
    location_id: Optional[int] = None,
    unassigned: Optional[bool] = None,
    sort: str = "name",
    order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Page[MachineRead]:
    """Retrieve paginated machines with eager location and part counts in a single query."""
    if status_filter not in ("active", "inactive", "all"):
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status must be one of: 'active', 'inactive', 'all'",
            code="validation_error",
        )

    sort_fields = {
        "name": Machine.name,
        "code": Machine.code,
        "created_at": Machine.created_at,
    }
    if sort not in sort_fields:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort parameter. Allowed options: {', '.join(sort_fields.keys())}",
            code="validation_error",
        )

    if order not in ("asc", "desc"):
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order must be 'asc' or 'desc'",
            code="validation_error",
        )

    if page < 1:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Page number must be greater than or equal to 1",
            code="validation_error",
        )

    if page_size < 1 or page_size > 100:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Page size must be between 1 and 100",
            code="validation_error",
        )

    conditions = []
    if status_filter == "active":
        conditions.append(Machine.is_active.is_(True))
    elif status_filter == "inactive":
        conditions.append(Machine.is_active.is_(False))

    if unassigned is True:
        conditions.append(Machine.location_id.is_(None))
    elif location_id is not None:
        conditions.append(Machine.location_id == location_id)

    if q and q.strip():
        search_pattern = f"%{escape_like(q.strip())}%"
        conditions.append(
            or_(
                Machine.name.ilike(search_pattern),
                Machine.code.ilike(search_pattern),
            )
        )

    count_stmt = select(func.count(Machine.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = db.scalar(count_stmt) or 0

    sort_col = sort_fields[sort]
    sort_expr = sort_col.asc() if order == "asc" else sort_col.desc()

    part_cnt_sub = _get_part_count_subquery()
    query = (
        select(Machine, part_cnt_sub)
        .options(joinedload(Machine.location))
        .order_by(sort_expr)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if conditions:
        query = query.where(*conditions)

    rows = db.execute(query).all()

    items = []
    for machine, p_cnt in rows:
        loc_brief = LocationBrief.model_validate(machine.location) if machine.location else None
        items.append(
            MachineRead(
                id=machine.id,
                name=machine.name,
                code=machine.code,
                is_active=machine.is_active,
                created_at=machine.created_at,
                location=loc_brief,
                part_count=p_cnt or 0,
            )
        )

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    return Page[MachineRead](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_machine_options(db: Session) -> List[MachineOption]:
    """Return minimal options list of active machines for select dropdowns."""
    query = (
        select(Machine)
        .where(Machine.is_active.is_(True))
        .order_by(Machine.name.asc())
    )
    machines = db.scalars(query).all()
    return [MachineOption.model_validate(m) for m in machines]


def get_machine_by_id(db: Session, machine_id: int) -> MachineRead:
    """Retrieve single machine by ID with part count and location details."""
    part_cnt_sub = _get_part_count_subquery()
    query = (
        select(Machine, part_cnt_sub)
        .options(joinedload(Machine.location))
        .where(Machine.id == machine_id)
    )
    row = db.execute(query).first()
    if not row:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine not found",
            code="machine_not_found",
        )

    machine, p_cnt = row
    loc_brief = LocationBrief.model_validate(machine.location) if machine.location else None
    return MachineRead(
        id=machine.id,
        name=machine.name,
        code=machine.code,
        is_active=machine.is_active,
        created_at=machine.created_at,
        location=loc_brief,
        part_count=p_cnt or 0,
    )


def create_machine(db: Session, data: MachineCreate) -> MachineRead:
    """Create a new machine record with duplicate code checks and active location validation."""
    # Check duplicate code (case-insensitive)
    existing_code = db.scalar(
        select(Machine.id).where(func.lower(Machine.code) == data.code.lower())
    )
    if existing_code:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Machine with code '{data.code}' already exists",
            code="duplicate_code",
            field="code",
        )

    # Validate location if specified
    if data.location_id is not None:
        loc = db.scalar(select(Location).where(Location.id == data.location_id))
        if not loc or not loc.is_active:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assigned location does not exist or is inactive",
                code="invalid_location",
                field="location_id",
            )

    new_machine = Machine(
        name=data.name,
        code=data.code,
        location_id=data.location_id,
        is_active=True,
    )
    db.add(new_machine)
    db.commit()
    db.refresh(new_machine)

    return get_machine_by_id(db, new_machine.id)


def update_machine(db: Session, machine_id: int, data: MachineUpdate) -> MachineRead:
    """Update machine attributes with validation and code uniqueness verification."""
    machine = db.scalar(select(Machine).where(Machine.id == machine_id))
    if not machine:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine not found",
            code="machine_not_found",
        )

    update_dict = data.model_dump(exclude_unset=True)
    if not update_dict:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be provided for update",
            code="empty_update",
        )

    # Check duplicate code
    if "code" in update_dict and update_dict["code"] != machine.code:
        existing_code = db.scalar(
            select(Machine.id).where(
                func.lower(Machine.code) == update_dict["code"].lower(),
                Machine.id != machine_id,
            )
        )
        if existing_code:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Machine with code '{update_dict['code']}' already exists",
                code="duplicate_code",
                field="code",
            )
        machine.code = update_dict["code"]

    if "name" in update_dict:
        machine.name = update_dict["name"]

    if "location_id" in update_dict:
        target_loc_id = update_dict["location_id"]
        if target_loc_id is None:
            machine.location_id = None
        elif target_loc_id != machine.location_id:
            loc = db.scalar(select(Location).where(Location.id == target_loc_id))
            if not loc or not loc.is_active:
                raise AppHTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Assigned location does not exist or is inactive",
                    code="invalid_location",
                    field="location_id",
                )
            machine.location_id = target_loc_id

    db.commit()
    db.refresh(machine)

    return get_machine_by_id(db, machine.id)


def deactivate_machine(db: Session, machine_id: int) -> MachineRead:
    """Deactivate a machine (safe soft delete, always allowed)."""
    machine = db.scalar(select(Machine).where(Machine.id == machine_id))
    if not machine:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine not found",
            code="machine_not_found",
        )

    if machine.is_active:
        machine.is_active = False
        db.commit()
        db.refresh(machine)

    return get_machine_by_id(db, machine.id)


def activate_machine(db: Session, machine_id: int) -> MachineRead:
    """Activate a previously deactivated machine."""
    machine = db.scalar(select(Machine).where(Machine.id == machine_id))
    if not machine:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine not found",
            code="machine_not_found",
        )

    if not machine.is_active:
        machine.is_active = True
        db.commit()
        db.refresh(machine)

    return get_machine_by_id(db, machine.id)

