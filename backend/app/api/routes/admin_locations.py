"""Admin endpoints for Location master data management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.location import LocationCreate, LocationOption, LocationRead, LocationUpdate
from app.services import location_service

router = APIRouter(
    prefix="/admin/locations",
    tags=["Admin Locations"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=Page[LocationRead])
def list_locations(
    q: Optional[str] = Query(None, description="Search term matching name, code, or city"),
    status: str = Query("all", description="Filter by active status ('active', 'inactive', 'all')"),
    sort: str = Query("name", description="Field to sort by ('name', 'code', 'city', 'created_at')"),
    order: str = Query("asc", description="Sort order ('asc' or 'desc')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List locations with pagination, search, sorting and aggregate counts."""
    return location_service.list_locations(
        db=db,
        q=q,
        status_filter=status,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/options", response_model=List[LocationOption])
def get_location_options(db: Session = Depends(get_db)):
    """Retrieve dropdown options for active locations."""
    return location_service.get_location_options(db=db)


@router.get("/{id}", response_model=LocationRead)
def get_location(id: int, db: Session = Depends(get_db)):
    """Get detailed location by ID."""
    return location_service.get_location_by_id(db=db, location_id=id)


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(data: LocationCreate, db: Session = Depends(get_db)):
    """Create a new location."""
    return location_service.create_location(db=db, data=data)


@router.patch("/{id}", response_model=LocationRead)
def update_location(id: int, data: LocationUpdate, db: Session = Depends(get_db)):
    """Update location details."""
    return location_service.update_location(db=db, location_id=id, data=data)


@router.post("/{id}/deactivate", response_model=LocationRead)
def deactivate_location(id: int, db: Session = Depends(get_db)):
    """Soft deactivate location if no active users or stock exist."""
    return location_service.deactivate_location(db=db, location_id=id)


@router.post("/{id}/activate", response_model=LocationRead)
def activate_location(id: int, db: Session = Depends(get_db)):
    """Reactivate a previously deactivated location."""
    return location_service.activate_location(db=db, location_id=id)

