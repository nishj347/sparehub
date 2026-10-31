"""Inventory and stock transaction business logic and row-locking updates."""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.models.enums import TransactionType
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.spare_part import SparePart
from app.models.user import User
from app.schemas.inventory import (
    InventoryAddLocation,
    InventoryRead,
    InventoryUpdate,
    StockAdjust,
    StockReceive,
)
from app.schemas.part import LocationBrief
from app.services.stock_rules import is_low_stock, is_out_of_stock


def get_inventory_by_id(db: Session, inventory_id: int) -> InventoryRead:
    """Retrieve single inventory row with eager location and computed stock flags."""
    inv = db.scalar(
        select(Inventory)
        .options(joinedload(Inventory.location))
        .where(Inventory.id == inventory_id)
    )
    if not inv:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
            code="not_found",
        )

    return InventoryRead(
        id=inv.id,
        part_id=inv.part_id,
        location_id=inv.location_id,
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


def add_part_location(
    db: Session,
    part_id: int,
    data: InventoryAddLocation,
    current_user: User,
) -> InventoryRead:
    """Assign spare part to a facility location with optional opening stock and audit transaction."""
    part = db.scalar(select(SparePart).where(SparePart.id == part_id))
    if not part:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found",
            code="not_found",
        )

    # Location must exist and be active
    loc = db.scalar(select(Location).where(Location.id == data.location_id))
    if not loc or not loc.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assigned location does not exist or is inactive",
            code="invalid_location",
            field="location_id",
        )

    # Must be unique per (part_id, location_id)
    existing = db.scalar(
        select(Inventory.id).where(
            Inventory.part_id == part_id,
            Inventory.location_id == data.location_id,
        )
    )
    if existing:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory record already exists for this part at the specified location",
            code="inventory_exists",
            field="location_id",
        )

    new_inv = Inventory(
        part_id=part_id,
        location_id=data.location_id,
        quantity=data.quantity,
        store_name=data.store_name,
        rack=data.rack,
        bin=data.bin,
        min_stock_level=data.min_stock_level,
    )
    db.add(new_inv)
    db.flush()

    if data.quantity > 0:
        tx = InventoryTransaction(
            part_id=part_id,
            location_id=data.location_id,
            user_id=current_user.id,
            transaction_type=TransactionType.RECEIVED,
            quantity_change=data.quantity,
            quantity_after=data.quantity,
            notes="Initial stock",
        )
        db.add(tx)

    db.commit()
    return get_inventory_by_id(db, new_inv.id)


def update_inventory(
    db: Session,
    inventory_id: int,
    data: InventoryUpdate,
) -> InventoryRead:
    """Update physical location coordinates or min stock alert (quantity immutable here)."""
    inv = db.scalar(select(Inventory).where(Inventory.id == inventory_id))
    if not inv:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
            code="not_found",
        )

    update_dict = data.model_dump(exclude_unset=True)
    if not update_dict:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be provided for update",
            code="empty_update",
        )

    if "store_name" in update_dict:
        inv.store_name = update_dict["store_name"]
    if "rack" in update_dict:
        inv.rack = update_dict["rack"]
    if "bin" in update_dict:
        inv.bin = update_dict["bin"]
    if "min_stock_level" in update_dict:
        inv.min_stock_level = update_dict["min_stock_level"]

    db.commit()
    return get_inventory_by_id(db, inv.id)


def receive_stock(
    db: Session,
    inventory_id: int,
    data: StockReceive,
    current_user: User,
) -> InventoryRead:
    """Add incoming stock quantity with row-level lock and immutable audit ledger record."""
    # Pessimistic row locking with SELECT ... FOR UPDATE
    inv = db.scalar(
        select(Inventory)
        .where(Inventory.id == inventory_id)
        .with_for_update()
    )
    if not inv:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
            code="not_found",
        )

    part = db.scalar(select(SparePart).where(SparePart.id == inv.part_id))
    if not part or not part.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot receive stock for an inactive spare part",
            code="part_inactive",
        )

    loc = db.scalar(select(Location).where(Location.id == inv.location_id))
    if not loc or not loc.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot receive stock at an inactive location",
            code="invalid_location",
        )

    inv.quantity += data.quantity

    tx = InventoryTransaction(
        part_id=inv.part_id,
        location_id=inv.location_id,
        user_id=current_user.id,
        transaction_type=TransactionType.RECEIVED,
        quantity_change=data.quantity,
        quantity_after=inv.quantity,
        notes=data.notes,
    )
    db.add(tx)
    db.commit()

    return get_inventory_by_id(db, inv.id)


def adjust_stock(
    db: Session,
    inventory_id: int,
    data: StockAdjust,
    current_user: User,
) -> InventoryRead:
    """Adjust physical on-hand stock count with row lock and signed delta audit ledger record."""
    inv = db.scalar(
        select(Inventory)
        .where(Inventory.id == inventory_id)
        .with_for_update()
    )
    if not inv:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
            code="not_found",
        )

    part = db.scalar(select(SparePart).where(SparePart.id == inv.part_id))
    if not part or not part.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot adjust stock for an inactive spare part",
            code="part_inactive",
        )

    loc = db.scalar(select(Location).where(Location.id == inv.location_id))
    if not loc or not loc.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot adjust stock at an inactive location",
            code="invalid_location",
        )

    delta = data.new_quantity - inv.quantity
    if delta == 0:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New quantity must be different from current quantity",
            code="no_change",
        )

    inv.quantity = data.new_quantity

    tx = InventoryTransaction(
        part_id=inv.part_id,
        location_id=inv.location_id,
        user_id=current_user.id,
        transaction_type=TransactionType.ADJUSTED,
        quantity_change=delta,
        quantity_after=data.new_quantity,
        notes=data.notes,
    )
    db.add(tx)
    db.commit()

    return get_inventory_by_id(db, inv.id)

