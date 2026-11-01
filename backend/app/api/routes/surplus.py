from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_employee_or_admin
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.surplus import (
    MySurplusInterestItem,
    SurplusFiltersResponse,
    SurplusInterestCreate,
    SurplusInterestResponse,
    SurplusItemDetail,
    SurplusItemList,
)
from app.services import surplus_service

router = APIRouter(prefix="/surplus", tags=["surplus"])


@router.get(
    "",
    response_model=Page[SurplusItemList],
    summary="Search / browse surplus items",
)
def list_surplus(
    q: Optional[str] = Query(None, description="Free-text search terms"),
    kind: Optional[str] = Query(None),
    location_id: Optional[int] = Query(None, ge=1),
    condition: Optional[str] = Query(None),
    sort: str = Query("newest"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=48),
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_or_admin),
):
    """Browse surplus listings with own-location-first sorting for regular users."""
    return surplus_service.list_surplus_items(
        db=db,
        user=user,
        q=q,
        kind=kind,
        location_id=location_id,
        condition=condition,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
        is_admin_view=False,
    )


@router.get(
    "/filters",
    response_model=SurplusFiltersResponse,
    summary="Available surplus filter options",
)
def get_filters(
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_or_admin),
):
    """Retrieve distinct kinds, conditions, and active locations with surplus listings."""
    return surplus_service.get_surplus_filters(db)


@router.get(
    "/mine/interests",
    response_model=Page[MySurplusInterestItem],
    summary="List caller's expressed interests",
)
def list_mine_interests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=48),
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_or_admin),
):
    """Retrieve all surplus interests registered by the authenticated user."""
    return surplus_service.list_my_interests(
        db=db,
        user=user,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{id}",
    response_model=SurplusItemDetail,
    summary="Surplus item detail",
)
def get_surplus_detail(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_or_admin),
):
    """Retrieve complete surplus item details with employee visibility safeguards."""
    return surplus_service.get_surplus_item_detail(
        db=db,
        item_id=id,
        user=user,
        is_admin_view=(user.role == UserRole.STORE_ADMIN),
    )


@router.put(
    "/{id}/interest",
    response_model=SurplusInterestResponse,
    summary="Express interest in a surplus item",
)
def express_interest(
    id: int,
    data: SurplusInterestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_or_admin),
):
    """Express or update interest in a surplus item and notify location admins."""
    return surplus_service.upsert_interest(
        db=db,
        item_id=id,
        user=user,
        data=data,
    )


@router.delete(
    "/{id}/interest",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw interest in a surplus item",
)
def withdraw_interest(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_or_admin),
):
    """Withdraw interest in a surplus item (idempotent)."""
    surplus_service.withdraw_interest(
        db=db,
        item_id=id,
        user=user,
    )
    return None

