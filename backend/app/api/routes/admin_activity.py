"""Admin Inventory Activity Ledger endpoint (GET /api/admin/activity)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.models.user import User
from app.schemas.activity import AdminActivityResponse
from app.services.activity_service import get_admin_activity

router = APIRouter(
    prefix="/admin/activity",
    tags=["Admin Activity"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "",
    response_model=AdminActivityResponse,
    summary="List all inventory activity ledger entries (Admin)",
)
def list_activity(
    q: Optional[str] = Query(None, description="Search by part name or part number"),
    employee: Optional[str] = Query(None, description="Search by employee name or employee ID"),
    type: Optional[str] = Query(None, description="Filter by transaction type (ISSUED, RECEIVED, ADJUSTED, all)"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    part_id: Optional[int] = Query(None, description="Filter by part ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD) inclusive"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD) inclusive"),
    sort: str = Query("created_at", description="Sort field: created_at, part_name, quantity, type"),
    order: str = Query("desc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminActivityResponse:
    """Retrieve paginated full inventory transaction ledger with summary statistics."""
    return get_admin_activity(
        db=db,
        q=q,
        employee=employee,
        tx_type=type,
        location_id=location_id,
        part_id=part_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )

