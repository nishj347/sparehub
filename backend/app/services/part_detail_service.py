"""Service layer for employee part detail endpoint (Module 7A)."""
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.core.storage import storage_service
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.machine import Machine
from app.models.part_machine import PartMachine
from app.models.spare_part import SparePart
from app.models.user import User
from app.schemas.part_detail import (
    EmployeePartDetail,
    LocationStockDetail,
    PublicLocationBrief,
    PublicMachineDetail,
    SpecItem,
)
from app.services.stock_rules import is_low_stock


def get_employee_part_detail(db: Session, part_id: int, current_user: User) -> EmployeePartDetail:
    """Retrieve full employee-facing details of an active spare part.

    Loads with exactly 3 constant queries:
    1. Active SparePart lookup
    2. Linked ACTIVE machines with location
    3. Active inventory rows at ACTIVE locations

    Inactive parts or non-existent IDs raise 404 not_found.
    """
    # 1. Query Part
    part = db.scalar(
        select(SparePart).where(
            SparePart.id == part_id,
            SparePart.is_active.is_(True),
        )
    )
    if not part:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found",
            code="not_found",
        )

    # 2. Query Active Machines linked to this part
    machines_stmt = (
        select(Machine)
        .options(joinedload(Machine.location))
        .join(PartMachine, PartMachine.machine_id == Machine.id)
        .where(
            PartMachine.part_id == part_id,
            Machine.is_active.is_(True),
        )
        .order_by(Machine.name.asc(), Machine.code.asc())
    )
    machines_rows = db.scalars(machines_stmt).all()
    machines_list: List[PublicMachineDetail] = [
        PublicMachineDetail(
            id=m.id,
            name=m.name,
            code=m.code,
            location_name=m.location.name if m.location else None,
        )
        for m in machines_rows
    ]

    # 3. Query Active Locations inventory rows
    inv_stmt = (
        select(Inventory)
        .options(joinedload(Inventory.location))
        .join(Location, Inventory.location_id == Location.id)
        .where(
            Inventory.part_id == part_id,
            Location.is_active.is_(True),
        )
    )
    inv_rows = db.scalars(inv_stmt).all()

    # Parse specifications (ordered from JSONB)
    specifications: List[SpecItem] = []
    if isinstance(part.specifications, dict):
        specifications = [SpecItem(key=k, value=str(v)) for k, v in part.specifications.items()]
    elif isinstance(part.specifications, list):
        for item in part.specifications:
            if isinstance(item, dict):
                specifications.append(
                    SpecItem(key=item.get("key", ""), value=str(item.get("value", "")))
                )

    # Compute per-row status and aggregate total
    total_quantity = sum(inv.quantity for inv in inv_rows)

    location_items: List[LocationStockDetail] = []
    for inv in inv_rows:
        if inv.quantity == 0:
            row_status = "OUT_OF_STOCK"
        elif is_low_stock(inv.quantity, inv.min_stock_level):
            row_status = "LOW_STOCK"
        else:
            row_status = "IN_STOCK"

        is_my_loc = bool(current_user.location_id and inv.location_id == current_user.location_id)

        location_items.append(
            LocationStockDetail(
                inventory_id=inv.id,
                location=PublicLocationBrief(
                    id=inv.location.id,
                    name=inv.location.name,
                    code=inv.location.code,
                    city=inv.location.city,
                ),
                quantity=inv.quantity,
                store_name=inv.store_name,
                rack=inv.rack,
                bin=inv.bin,
                availability_status=row_status,
                is_my_location=is_my_loc,
            )
        )

    # Sort locations: caller's own location first (is_my_location == True),
    # then quantity descending, then location name ascending
    location_items.sort(
        key=lambda x: (
            0 if x.is_my_location else 1,
            -x.quantity,
            x.location.name,
        )
    )

    # Part-level overall availability status
    if total_quantity == 0:
        overall_status = "OUT_OF_STOCK"
    elif any(item.availability_status == "LOW_STOCK" for item in location_items if item.quantity > 0):
        # Or if any active row is low stock and total > 0
        overall_status = "LOW_STOCK"
    else:
        overall_status = "IN_STOCK"

    return EmployeePartDetail(
        id=part.id,
        part_number=part.part_number,
        name=part.name,
        category=part.category,
        manufacturer=part.manufacturer,
        description=part.description,
        image_url=storage_service.public_url(part.image_path) if part.image_path else None,
        specifications=specifications,
        machines=machines_list,
        total_quantity=total_quantity,
        availability_status=overall_status,
        locations=location_items,
    )

