# backend/app/api/routes/parts.py
"""Employee‑facing part discovery endpoints (Module 6A)."""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import require_employee_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.part_public import PartCard
from app.services.part_search_service import search_parts


router = APIRouter(prefix="/parts", tags=["parts"])

@router.get(
    "",
    response_model=Page[PartCard],
    summary="Search / browse spare parts (employee view)",
)
def list_parts(
    q: Optional[str] = Query(None, description="Free‑text search terms"),
    category: Optional[str] = Query(None),
    machine_id: Optional[int] = Query(None, ge=1),
    location_id: Optional[int] = Query(None, ge=1),
    availability: str = Query(
        "all", regex="^(all|available|my_location|location)$"
    ),
    sort: str = Query("relevance"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=48),
    db: Session = Depends(get_db),
    user: "User" = Depends(require_employee_or_admin),
):
    """Employee search endpoint – respects all Module 6A rules."""
    return search_parts(
        db=db,
        user=user,
        q=q,
        category=category,
        machine_id=machine_id,
        location_id=location_id,
        availability=availability,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )

# Filter endpoint – returns distinct categories, active machines, active locations
from pydantic import BaseModel
from app.models.spare_part import SparePart
from app.models.machine import Machine
from app.models.inventory import Inventory
from app.models.location import Location

class FiltersResponse(BaseModel):
    categories: List[str]
    machines: List[dict]
    locations: List[dict]

@router.get(
    "/filters",
    response_model=FiltersResponse,
    summary="Return filter options for active parts",
)
def get_filters(
    db: Session = Depends(get_db),
    user: "User" = Depends(require_employee_or_admin),
):
    # categories
    cats = db.scalars(select(SparePart.category).distinct()).all()

    # machines linked to active parts (active only)
    machine_stmt = (
        select(Machine.id, Machine.name, Machine.code)
        .join(SparePart.machines)
        .where(SparePart.is_active.is_(True), Machine.is_active.is_(True))
        .distinct()
    )
    machines = [
        {"id": m.id, "name": m.name, "code": m.code}
        for m in db.execute(machine_stmt).fetchall()
    ]

    # active locations with stock for active parts
    loc_stmt = (
        select(Location.id, Location.name, Location.code)
        .join(Inventory, Inventory.location_id == Location.id)
        .join(SparePart, Inventory.part_id == SparePart.id)
        .where(SparePart.is_active.is_(True), Location.is_active.is_(True))
        .distinct()
    )
    locations = [
        {"id": l.id, "name": l.name, "code": l.code}
        for l in db.execute(loc_stmt).fetchall()
    ]
    return FiltersResponse(categories=cats, machines=machines, locations=locations)


from app.schemas.part_detail import EmployeePartDetail
from app.services.part_detail_service import get_employee_part_detail


@router.get(
    "/{part_id}",
    response_model=EmployeePartDetail,
    summary="Get employee spare part detail",
)
def get_part_detail(
    part_id: int,
    db: Session = Depends(get_db),
    user: "User" = Depends(require_employee_or_admin),
) -> EmployeePartDetail:
    """Retrieve full employee-facing details of an active spare part."""
    return get_employee_part_detail(db=db, part_id=part_id, current_user=user)

