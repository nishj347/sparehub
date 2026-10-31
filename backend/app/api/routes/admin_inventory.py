"""Admin endpoints for Inventory coordinates and stock operations."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.inventory import (
    InventoryRead,
    InventoryUpdate,
    StockAdjust,
    StockReceive,
)
from app.services import inventory_service

router = APIRouter(
    prefix="/admin/inventory",
    tags=["Admin Inventory"],
    dependencies=[Depends(require_admin)],
)


@router.patch("/{inventory_id}", response_model=InventoryRead)
def update_inventory(
    inventory_id: int,
    data: InventoryUpdate,
    db: Session = Depends(get_db),
):
    """Update inventory coordinates or min stock alert threshold (quantity immutable here)."""
    return inventory_service.update_inventory(
        db=db,
        inventory_id=inventory_id,
        data=data,
    )


@router.post("/{inventory_id}/receive", response_model=InventoryRead)
def receive_stock(
    inventory_id: int,
    data: StockReceive,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Receive incoming stock into inventory with row lock and immutable audit ledger record."""
    return inventory_service.receive_stock(
        db=db,
        inventory_id=inventory_id,
        data=data,
        current_user=current_user,
    )


@router.post("/{inventory_id}/adjust", response_model=InventoryRead)
def adjust_stock(
    inventory_id: int,
    data: StockAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Adjust physical stock count with row lock and signed delta audit ledger record."""
    return inventory_service.adjust_stock(
        db=db,
        inventory_id=inventory_id,
        data=data,
        current_user=current_user,
    )

