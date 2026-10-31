"""Admin endpoints for Spare Parts catalog management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, require_admin
from app.core.exceptions import AppHTTPException
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.inventory import InventoryAddLocation, InventoryRead
from app.schemas.part import PartCreate, PartDetail, PartListItem, PartUpdate
from app.services import inventory_service, part_service

settings = get_settings()

router = APIRouter(
    prefix="/admin/parts",
    tags=["Admin Spare Parts"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=Page[PartListItem])
def list_parts(
    q: Optional[str] = Query(None, description="Search term matching part number, name, category, or machines"),
    category: Optional[str] = Query(None, description="Filter by component category"),
    status: str = Query("all", description="Filter by active status ('active', 'inactive', 'all')"),
    stock: str = Query("all", description="Filter by stock level ('all', 'in_stock', 'low', 'out')"),
    location_id: Optional[int] = Query(None, description="Filter by assigned plant location ID"),
    machine_id: Optional[int] = Query(None, description="Filter by linked machine equipment ID"),
    sort: str = Query("name", description="Sort field ('name', 'part_number', 'category', 'total_quantity', 'updated_at')"),
    order: str = Query("asc", description="Sort order ('asc' or 'desc')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated catalog spare parts list with single-query stock metrics."""
    return part_service.list_parts(
        db=db,
        q=q,
        category=category,
        status_filter=status,
        stock_filter=stock,
        location_id=location_id,
        machine_id=machine_id,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db)):
    """Retrieve unique component categories sorted alphabetically (declared before /{id})."""
    return part_service.get_distinct_categories(db=db)


@router.get("/{id}", response_model=PartDetail)
def get_part(id: int, db: Session = Depends(get_db)):
    """Retrieve full spare part details, inventory breakdown, and recent transactions."""
    return part_service.get_part_by_id(db=db, part_id=id)


@router.post("", response_model=PartDetail, status_code=status.HTTP_201_CREATED)
def create_part(
    data: PartCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new catalog spare part with optional machine links and opening inventory."""
    return part_service.create_part(db=db, data=data, current_user=current_user)


@router.patch("/{id}", response_model=PartDetail)
def update_part(id: int, data: PartUpdate, db: Session = Depends(get_db)):
    """Update spare part attributes and machine relationships (part_number is immutable)."""
    return part_service.update_part(db=db, part_id=id, data=data)


@router.post("/{id}/image", response_model=PartDetail)
async def upload_part_image(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload or replace part image with magic bytes verification and chunked size enforcement."""
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    chunk_size = 1024 * 64  # 64 KB
    data = bytearray()

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise AppHTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed upload size of {settings.MAX_UPLOAD_MB}MB.",
                code="file_too_large",
            )

    return part_service.upload_part_image(db=db, part_id=id, file_bytes=bytes(data))


@router.delete("/{id}/image", response_model=PartDetail)
def delete_part_image(id: int, db: Session = Depends(get_db)):
    """Remove part image and clear associated storage asset."""
    return part_service.delete_part_image(db=db, part_id=id)


@router.post("/{id}/deactivate", response_model=PartDetail)
def deactivate_part(id: int, db: Session = Depends(get_db)):
    """Soft deactivate spare part (always allowed, preserves inventory history)."""
    return part_service.deactivate_part(db=db, part_id=id)


@router.post("/{id}/activate", response_model=PartDetail)
def activate_part(id: int, db: Session = Depends(get_db)):
    """Reactivate previously deactivated spare part."""
    return part_service.activate_part(db=db, part_id=id)


@router.post("/{id}/inventory", response_model=InventoryRead, status_code=status.HTTP_201_CREATED)
def add_part_location(
    id: int,
    data: InventoryAddLocation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign spare part to a new facility location with optional opening stock."""
    return inventory_service.add_part_location(
        db=db,
        part_id=id,
        data=data,
        current_user=current_user,
    )

