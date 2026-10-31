"""Admin endpoints for Machine master data management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.machine import (
    MachineCreate,
    MachineOption,
    MachineRead,
    MachineUpdate,
)
from app.services import machine_service

router = APIRouter(
    prefix="/admin/machines",
    tags=["Admin Machines"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=Page[MachineRead])
def list_machines(
    q: Optional[str] = Query(None, description="Search term matching machine name or code"),
    status: str = Query("all", description="Filter by active status ('active', 'inactive', 'all')"),
    location_id: Optional[int] = Query(None, description="Filter by assigned location ID"),
    unassigned: Optional[bool] = Query(None, description="Filter machines not assigned to any location"),
    sort: str = Query("name", description="Field to sort by ('name', 'code', 'created_at')"),
    order: str = Query("asc", description="Sort order ('asc' or 'desc')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List machines with pagination, filtering, search, sorting and part counts."""
    return machine_service.list_machines(
        db=db,
        q=q,
        status_filter=status,
        location_id=location_id,
        unassigned=unassigned,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/options", response_model=List[MachineOption])
def get_machine_options(db: Session = Depends(get_db)):
    """Retrieve dropdown options for active machines."""
    return machine_service.get_machine_options(db=db)


@router.get("/{id}", response_model=MachineRead)
def get_machine(id: int, db: Session = Depends(get_db)):
    """Get detailed machine by ID."""
    return machine_service.get_machine_by_id(db=db, machine_id=id)


@router.post("", response_model=MachineRead, status_code=status.HTTP_201_CREATED)
def create_machine(data: MachineCreate, db: Session = Depends(get_db)):
    """Create a new machine."""
    return machine_service.create_machine(db=db, data=data)


@router.patch("/{id}", response_model=MachineRead)
def update_machine(id: int, data: MachineUpdate, db: Session = Depends(get_db)):
    """Update machine details."""
    return machine_service.update_machine(db=db, machine_id=id, data=data)


@router.post("/{id}/deactivate", response_model=MachineRead)
def deactivate_machine(id: int, db: Session = Depends(get_db)):
    """Soft deactivate a machine."""
    return machine_service.deactivate_machine(db=db, machine_id=id)


@router.post("/{id}/activate", response_model=MachineRead)
def activate_machine(id: int, db: Session = Depends(get_db)):
    """Reactivate a previously deactivated machine."""
    return machine_service.activate_machine(db=db, machine_id=id)

