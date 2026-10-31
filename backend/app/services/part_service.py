"""Spare parts catalog management business logic and database queries."""
import math
from typing import List, Optional
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.core.storage import storage_service
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.machine import Machine
from app.models.spare_part import SparePart
from app.models.user import User
from app.schemas.common import Page
from app.schemas.part import (
    InventoryItemDetail,
    LocationBrief,
    MachineBrief,
    PartCreate,
    PartDetail,
    PartListItem,
    PartUpdate,
    SpecItem,
    TransactionBrief,
    UserBrief,
)
from app.services.location_service import escape_like
from app.services.stock_rules import (
    is_low_stock,
    is_out_of_stock,
    is_part_out_of_stock,
    part_location_count_subquery,
    part_low_stock_subquery,
    part_out_of_stock_subquery,
    part_total_quantity_subquery,
)


def list_parts(
    db: Session,
    q: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: str = "all",
    stock_filter: str = "all",
    location_id: Optional[int] = None,
    machine_id: Optional[int] = None,
    sort: str = "name",
    order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Page[PartListItem]:
    """Retrieve paginated spare parts list with single-query aggregate metrics and eager machines."""
    if status_filter not in ("active", "inactive", "all"):
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status must be one of: 'active', 'inactive', 'all'",
            code="validation_error",
        )

    if stock_filter not in ("all", "in_stock", "low", "out"):
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stock filter must be one of: 'all', 'in_stock', 'low', 'out'",
            code="validation_error",
        )

    allowed_sorts = {
        "name": SparePart.name,
        "part_number": SparePart.part_number,
        "category": SparePart.category,
        "total_quantity": "total_quantity",
        "updated_at": SparePart.updated_at,
    }
    if sort not in allowed_sorts:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort parameter. Allowed options: {', '.join(allowed_sorts.keys())}",
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

    # Subqueries for aggregate metrics
    total_qty_sub = part_total_quantity_subquery(SparePart.id)
    loc_cnt_sub = part_location_count_subquery(SparePart.id)
    low_stock_sub = part_low_stock_subquery(SparePart.id)
    out_of_stock_sub = part_out_of_stock_subquery(SparePart.id)

    conditions = []

    # Status filter
    if status_filter == "active":
        conditions.append(SparePart.is_active.is_(True))
    elif status_filter == "inactive":
        conditions.append(SparePart.is_active.is_(False))

    # Category filter
    if category and category.strip():
        conditions.append(SparePart.category == category.strip())

    # Stock filter
    if stock_filter == "in_stock":
        conditions.append(total_qty_sub > 0)
    elif stock_filter == "low":
        conditions.append(low_stock_sub.is_(True))
    elif stock_filter == "out":
        conditions.append(total_qty_sub == 0)

    # Location filter
    if location_id is not None:
        conditions.append(SparePart.inventory_items.any(Inventory.location_id == location_id))

    # Machine filter
    if machine_id is not None:
        conditions.append(SparePart.machines.any(Machine.id == machine_id))

    # Search filter q across part fields and machine names/codes
    if q and q.strip():
        pattern = f"%{escape_like(q.strip())}%"
        conditions.append(
            or_(
                SparePart.part_number.ilike(pattern),
                SparePart.name.ilike(pattern),
                SparePart.category.ilike(pattern),
                SparePart.manufacturer.ilike(pattern),
                SparePart.machines.any(
                    or_(
                        Machine.name.ilike(pattern),
                        Machine.code.ilike(pattern),
                    )
                ),
            )
        )

    # Count matching parts
    count_stmt = select(func.count(SparePart.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = db.scalar(count_stmt) or 0

    # Sorting
    if sort == "total_quantity":
        sort_col = total_qty_sub
    else:
        sort_col = allowed_sorts[sort]

    sort_expr = sort_col.asc() if order == "asc" else sort_col.desc()
    secondary_sort = SparePart.id.asc() if order == "asc" else SparePart.id.desc()

    # Query items with subqueries in a single round trip
    stmt = (
        select(
            SparePart,
            total_qty_sub.label("total_quantity"),
            loc_cnt_sub.label("location_count"),
            low_stock_sub.label("low_stock"),
            out_of_stock_sub.label("out_of_stock"),
        )
        .options(selectinload(SparePart.machines))
        .order_by(sort_expr, secondary_sort)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if conditions:
        stmt = stmt.where(*conditions)

    rows = db.execute(stmt).all()

    items = []
    for part, total_qty, loc_cnt, is_low, is_out in rows:
        machines_brief = [
            MachineBrief(id=m.id, name=m.name, code=m.code)
            for m in part.machines
        ]
        items.append(
            PartListItem(
                id=part.id,
                part_number=part.part_number,
                name=part.name,
                category=part.category,
                manufacturer=part.manufacturer,
                image_url=storage_service.public_url(part.image_path),
                is_active=part.is_active,
                total_quantity=total_qty or 0,
                location_count=loc_cnt or 0,
                low_stock=bool(is_low),
                out_of_stock=bool(is_out),
                machines=machines_brief,
                updated_at=part.updated_at,
            )
        )

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    return Page[PartListItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_distinct_categories(db: Session) -> List[str]:
    """Retrieve unique component categories sorted alphabetically."""
    stmt = (
        select(distinct(SparePart.category))
        .where(SparePart.category.isnot(None), SparePart.category != "")
        .order_by(SparePart.category.asc())
    )
    categories = db.scalars(stmt).all()
    return list(categories)


def get_part_by_id(db: Session, part_id: int) -> PartDetail:
    """Retrieve full part detail including inventory breakdown and recent ledger transactions."""
    part = db.scalar(
        select(SparePart)
        .options(
            selectinload(SparePart.machines),
            selectinload(SparePart.inventory_items).joinedload(Inventory.location),
        )
        .where(SparePart.id == part_id)
    )
    if not part:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found",
            code="not_found",
        )

    total_quantity = sum(i.quantity for i in part.inventory_items)
    location_count = len(part.inventory_items)
    low_stock = any(is_low_stock(i.quantity, i.min_stock_level) for i in part.inventory_items)
    out_of_stock = is_part_out_of_stock(total_quantity)

    # Format specifications
    specs: List[SpecItem] = []
    if isinstance(part.specifications, dict):
        specs = [SpecItem(key=k, value=str(v)) for k, v in part.specifications.items()]
    elif isinstance(part.specifications, list):
        for item in part.specifications:
            if isinstance(item, dict):
                specs.append(SpecItem(key=item.get("key", ""), value=str(item.get("value", ""))))

    # Format machines
    machines = [
        MachineBrief(id=m.id, name=m.name, code=m.code)
        for m in sorted(part.machines, key=lambda m: m.name)
    ]

    # Format inventory rows
    inventory_items = []
    for inv in sorted(part.inventory_items, key=lambda i: i.location.name if i.location else ""):
        inventory_items.append(
            InventoryItemDetail(
                id=inv.id,
                location=LocationBrief.model_validate(inv.location),
                quantity=inv.quantity,
                store_name=inv.store_name,
                rack=inv.rack,
                bin=inv.bin,
                min_stock_level=inv.min_stock_level,
                low_stock=is_low_stock(inv.quantity, inv.min_stock_level),
                out_of_stock=is_out_of_stock(inv.quantity),
                updated_at=inv.updated_at,
            )
        )

    # Fetch last 10 transactions for this part
    tx_stmt = (
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.user),
            joinedload(InventoryTransaction.location),
        )
        .where(InventoryTransaction.part_id == part_id)
        .order_by(InventoryTransaction.created_at.desc(), InventoryTransaction.id.desc())
        .limit(10)
    )
    tx_rows = db.scalars(tx_stmt).all()
    recent_transactions = []
    for tx in tx_rows:
        u_brief = UserBrief.model_validate(tx.user) if tx.user else None
        recent_transactions.append(
            TransactionBrief(
                id=tx.id,
                created_at=tx.created_at,
                type=tx.transaction_type,
                quantity_change=tx.quantity_change,
                quantity_after=tx.quantity_after,
                user=u_brief,
                location=LocationBrief.model_validate(tx.location),
                notes=tx.notes,
            )
        )

    return PartDetail(
        id=part.id,
        part_number=part.part_number,
        name=part.name,
        category=part.category,
        manufacturer=part.manufacturer,
        description=part.description,
        specifications=specs,
        image_url=storage_service.public_url(part.image_path),
        is_active=part.is_active,
        created_at=part.created_at,
        updated_at=part.updated_at,
        total_quantity=total_quantity,
        location_count=location_count,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        machines=machines,
        inventory=inventory_items,
        recent_transactions=recent_transactions,
    )


def create_part(db: Session, data: PartCreate, current_user: User) -> PartDetail:
    """Create a new catalog spare part with optional machine links and opening inventory."""
    # Check duplicate part_number (case-insensitive)
    existing = db.scalar(
        select(SparePart.id).where(func.lower(SparePart.part_number) == data.part_number.lower())
    )
    if existing:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Part with part number '{data.part_number}' already exists",
            code="duplicate_part_number",
            field="part_number",
        )

    # Validate machine_ids: all must exist and be ACTIVE
    linked_machines = []
    if data.machine_ids:
        machines = db.scalars(
            select(Machine).where(Machine.id.in_(data.machine_ids))
        ).all()
        found_map = {m.id: m for m in machines}
        missing_or_inactive = [
            m_id for m_id in data.machine_ids
            if m_id not in found_map or not found_map[m_id].is_active
        ]
        if missing_or_inactive:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="One or more specified machines do not exist or are inactive",
                code="invalid_machine",
                field="machine_ids",
            )
        linked_machines = [found_map[m_id] for m_id in data.machine_ids]

    # Validate initial_stock if provided
    init_stock = data.initial_stock
    if init_stock:
        loc = db.scalar(select(Location).where(Location.id == init_stock.location_id))
        if not loc or not loc.is_active:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assigned location does not exist or is inactive",
                code="invalid_location",
                field="location_id",
            )

    new_part = SparePart(
        part_number=data.part_number,
        name=data.name,
        category=data.category,
        manufacturer=data.manufacturer,
        description=data.description,
        specifications=data.specifications,
        is_active=True,
    )
    if linked_machines:
        new_part.machines = linked_machines

    db.add(new_part)
    try:
        db.flush()  # assign new_part.id

        if init_stock:
            new_inv = Inventory(
                part_id=new_part.id,
                location_id=init_stock.location_id,
                quantity=init_stock.quantity,
                store_name=init_stock.store_name,
                rack=init_stock.rack,
                bin=init_stock.bin,
                min_stock_level=init_stock.min_stock_level,
            )
            db.add(new_inv)
            db.flush()

            if init_stock.quantity > 0:
                tx = InventoryTransaction(
                    part_id=new_part.id,
                    location_id=init_stock.location_id,
                    user_id=current_user.id,
                    transaction_type="RECEIVED",
                    quantity_change=init_stock.quantity,
                    quantity_after=init_stock.quantity,
                    notes="Initial stock",
                )
                db.add(tx)

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        err_msg = str(getattr(exc, "orig", exc)).lower()
        if "part_number" in err_msg or "uq_spare_parts_part_number" in err_msg:
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Part with part number '{data.part_number}' already exists",
                code="duplicate_part_number",
                field="part_number",
            )
        raise

    return get_part_by_id(db, new_part.id)


def update_part(db: Session, part_id: int, data: PartUpdate) -> PartDetail:
    """Update spare part attributes and machine relationships (part_number is immutable)."""
    part = db.scalar(
        select(SparePart)
        .options(selectinload(SparePart.machines))
        .where(SparePart.id == part_id)
    )
    if not part:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found",
            code="not_found",
        )

    update_dict = data.model_dump(exclude_unset=True)
    if not update_dict:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be provided for update",
            code="empty_update",
        )

    if "name" in update_dict:
        part.name = update_dict["name"]

    if "category" in update_dict:
        part.category = update_dict["category"]

    if "manufacturer" in update_dict:
        part.manufacturer = update_dict["manufacturer"]

    if "description" in update_dict:
        part.description = update_dict["description"]

    if "specifications" in update_dict:
        part.specifications = update_dict["specifications"]

    if "machine_ids" in update_dict:
        target_ids = set(update_dict["machine_ids"] or [])
        current_ids = {m.id for m in part.machines}
        added_ids = target_ids - current_ids

        # Added machines must exist and be ACTIVE. Existing machines may remain even if inactive.
        if added_ids:
            machines = db.scalars(select(Machine).where(Machine.id.in_(added_ids))).all()
            found_map = {m.id: m for m in machines}
            for m_id in added_ids:
                if m_id not in found_map or not found_map[m_id].is_active:
                    raise AppHTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="One or more newly added machines do not exist or are inactive",
                        code="invalid_machine",
                        field="machine_ids",
                    )

        all_target_machines = db.scalars(select(Machine).where(Machine.id.in_(target_ids))).all()
        part.machines = all_target_machines

    db.commit()
    return get_part_by_id(db, part.id)


def upload_part_image(db: Session, part_id: int, file_bytes: bytes) -> PartDetail:
    """Store uploaded image bytes, update part.image_path, delete previous asset on commit."""
    part = db.scalar(select(SparePart).where(SparePart.id == part_id))
    if not part:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found",
            code="not_found",
        )

    # Save new image first
    new_relative_path = storage_service.save_image(file_bytes)
    old_relative_path = part.image_path

    part.image_path = new_relative_path
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage_service.delete(new_relative_path)
        raise

    # Delete previous asset after successful DB commit
    if old_relative_path and old_relative_path != new_relative_path:
        storage_service.delete(old_relative_path)

    return get_part_by_id(db, part.id)


def delete_part_image(db: Session, part_id: int) -> PartDetail:
    """Clear image reference on part and remove image file from disk."""
    part = db.scalar(select(SparePart).where(SparePart.id == part_id))
    if not part:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found",
            code="not_found",
        )

    old_relative_path = part.image_path
    if old_relative_path:
        part.image_path = None
        db.commit()
        storage_service.delete(old_relative_path)

    return get_part_by_id(db, part.id)


def deactivate_part(db: Session, part_id: int) -> PartDetail:
    """Soft deactivate spare part (always allowed, idempotent)."""
    part = db.scalar(select(SparePart).where(SparePart.id == part_id))
    if not part:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found",
            code="not_found",
        )

    if part.is_active:
        part.is_active = False
        db.commit()

    return get_part_by_id(db, part.id)


def activate_part(db: Session, part_id: int) -> PartDetail:
    """Activate previously deactivated spare part (idempotent)."""
    part = db.scalar(select(SparePart).where(SparePart.id == part_id))
    if not part:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found",
            code="not_found",
        )

    if not part.is_active:
        part.is_active = True
        db.commit()

    return get_part_by_id(db, part.id)

