from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import require_admin
from app.core.exceptions import AppHTTPException
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.surplus import (
    AdminSurplusInterestRecord,
    SurplusItemCreate,
    SurplusItemDetail,
    SurplusItemList,
    SurplusItemUpdate,
    SurplusStatusUpdate,
)
from app.services import surplus_service

settings = get_settings()
router = APIRouter(prefix="/admin/surplus", tags=["admin-surplus"])


@router.get(
    "",
    response_model=Page[SurplusItemList],
    summary="List all surplus listings (Admin)",
)
def list_admin_surplus(
    q: Optional[str] = Query(None, description="Free-text search terms"),
    kind: Optional[str] = Query(None),
    location_id: Optional[int] = Query(None, ge=1),
    condition: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    created_by: Optional[int] = Query(None, ge=1),
    sort: str = Query("newest"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=48),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin view of all surplus items across the enterprise including archived statuses."""
    return surplus_service.list_surplus_items(
        db=db,
        user=admin,
        q=q,
        kind=kind,
        location_id=location_id,
        condition=condition,
        status_filter=status,
        created_by=created_by,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
        is_admin_view=True,
    )


@router.post(
    "",
    response_model=SurplusItemDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new surplus listing",
)
def create_surplus_item(
    data: SurplusItemCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new surplus material, machine, or spare part listing."""
    return surplus_service.create_surplus_item(
        db=db,
        admin=admin,
        data=data,
    )


@router.patch(
    "/{id}",
    response_model=SurplusItemDetail,
    summary="Update surplus item details",
)
def update_surplus_item(
    id: int,
    data: SurplusItemUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update editable fields of an existing surplus item."""
    return surplus_service.update_surplus_item(
        db=db,
        item_id=id,
        admin=admin,
        data=data,
    )


@router.post(
    "/{id}/status",
    response_model=SurplusItemDetail,
    summary="Update surplus listing lifecycle status",
)
def update_surplus_status(
    id: int,
    data: SurplusStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Transition listing between AVAILABLE, RESERVED, CLAIMED, and WITHDRAWN."""
    return surplus_service.update_surplus_status(
        db=db,
        item_id=id,
        admin=admin,
        new_status=data.status,
    )


@router.post(
    "/{id}/image",
    response_model=SurplusItemDetail,
    summary="Upload or replace surplus item image",
)
async def upload_surplus_image(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Upload item image with magic bytes verification and size enforcement."""
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

    surplus_service.upload_surplus_image(db=db, item_id=id, file_bytes=bytes(data))
    return surplus_service.get_surplus_item_detail(db=db, item_id=id, user=admin, is_admin_view=True)


@router.delete(
    "/{id}/image",
    response_model=SurplusItemDetail,
    summary="Remove surplus item image",
)
def delete_surplus_image(
    id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Remove surplus image and clear stored file asset."""
    surplus_service.delete_surplus_image(db=db, item_id=id)
    return surplus_service.get_surplus_item_detail(db=db, item_id=id, user=admin, is_admin_view=True)


@router.get(
    "/{id}/interests",
    response_model=List[AdminSurplusInterestRecord],
    summary="List all interest expressions for an item",
)
def list_item_interests(
    id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Retrieve all users who expressed interest in this surplus listing."""
    return surplus_service.get_item_interests(
        db=db,
        item_id=id,
        admin=admin,
    )

