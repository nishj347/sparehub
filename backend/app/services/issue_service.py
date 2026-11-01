"""Atomic issue-part business logic with idempotency, row-locking, and admin notifications."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.models.enums import TransactionType, UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.notification import Notification
from app.models.spare_part import SparePart
from app.models.user import User
from app.schemas.issue import (
    IssueEmployeeBrief,
    IssueLocationBrief,
    IssuePartBrief,
    IssueRequest,
    IssueResponse,
)


def _build_response(
    tx: InventoryTransaction,
    inv: Inventory,
    part: SparePart,
    location: Location,
    user: User,
    *,
    idempotent_replay: bool,
) -> IssueResponse:
    """Construct IssueResponse from ORM objects already loaded in the session."""
    return IssueResponse(
        transaction_id=tx.id,
        issued_at=tx.created_at,
        employee=IssueEmployeeBrief(employee_id=user.employee_id, name=user.name),
        part=IssuePartBrief(id=part.id, part_number=part.part_number, name=part.name),
        location=IssueLocationBrief(id=location.id, name=location.name, code=location.code),
        store_name=inv.store_name,
        rack=inv.rack,
        bin=inv.bin,
        quantity_issued=abs(tx.quantity_change),
        quantity_remaining=tx.quantity_after,
        message=f"{abs(tx.quantity_change)} unit(s) issued successfully.",
        idempotent_replay=idempotent_replay,
    )


def _load_existing_tx(db: Session, user_id: int, idempotency_key: str) -> InventoryTransaction | None:
    """Return an existing transaction for this (user_id, idempotency_key), or None."""
    return db.scalar(
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.part),
            joinedload(InventoryTransaction.location),
        )
        .where(
            InventoryTransaction.user_id == user_id,
            InventoryTransaction.idempotency_key == idempotency_key,
        )
    )


def issue_part(db: Session, user: User, data: IssueRequest) -> tuple[IssueResponse, int]:
    """
    Atomically deduct stock and write the ledger row.

    Returns (IssueResponse, http_status_code).
    Status is 201 for a new issue, 200 for an idempotent replay.
    """
    if data.inventory_id is None:
        if data.part_id and data.location_id:
            resolved_id = db.scalar(
                select(Inventory.id).where(
                    Inventory.part_id == data.part_id,
                    Inventory.location_id == data.location_id,
                )
            )
            if not resolved_id:
                raise AppHTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Inventory record not found.",
                    code="not_found",
                )
            data.inventory_id = resolved_id
        else:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either inventory_id or (part_id, location_id) must be provided.",
                code="validation_error",
                field="inventory_id",
            )

    # ── 1. Idempotency check (before locking) ───────────────────────────────
    existing_tx = _load_existing_tx(db, user.id, data.idempotency_key)
    if existing_tx is not None:
        target_inv = db.scalar(
            select(Inventory)
            .options(joinedload(Inventory.part), joinedload(Inventory.location))
            .where(Inventory.id == data.inventory_id)
        )
        if (
            target_inv is None
            or existing_tx.part_id != target_inv.part_id
            or existing_tx.location_id != target_inv.location_id
            or abs(existing_tx.quantity_change) != data.quantity
        ):
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The idempotency_key was already used with different parameters. "
                    "Use a new key for a different operation."
                ),
                code="idempotency_conflict",
                field="idempotency_key",
            )
        return _build_response(
            existing_tx, target_inv, existing_tx.part, existing_tx.location, user, idempotent_replay=True
        ), 200

    # ── 2. Lock the inventory row ────────────────────────────────────────────
    inv = db.scalar(
        select(Inventory)
        .where(Inventory.id == data.inventory_id)
        .with_for_update()
    )
    if inv is None:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found.",
            code="not_found",
        )

    part = db.scalar(select(SparePart).where(SparePart.id == inv.part_id))
    loc = db.scalar(select(Location).where(Location.id == inv.location_id))

    # ── 3. Business-rule guards ──────────────────────────────────────────────
    if not part or not part.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot issue an inactive spare part.",
            code="part_inactive",
        )

    if not loc or not loc.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot issue from an inactive location.",
            code="location_inactive",
        )

    if data.quantity > inv.quantity:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Insufficient stock: requested {data.quantity} but only "
                f"{inv.quantity} available."
            ),
            code="insufficient_stock",
            field="quantity",
        )

    # ── 4. Deduct and write ledger ───────────────────────────────────────────
    inv.quantity -= data.quantity
    tx = InventoryTransaction(
        part_id=inv.part_id,
        location_id=inv.location_id,
        user_id=user.id,
        transaction_type=TransactionType.ISSUED,
        quantity_change=-data.quantity,
        quantity_after=inv.quantity,
        notes=data.notes,
        idempotency_key=data.idempotency_key,
    )
    db.add(tx)

    # ── 5. Flush to get tx.id before creating notifications ─────────────────
    try:
        db.flush()
    except IntegrityError:
        # Race: another request with same key committed first — replay it
        db.rollback()
        existing_tx = _load_existing_tx(db, user.id, data.idempotency_key)
        target_inv = db.scalar(
            select(Inventory)
            .options(joinedload(Inventory.part), joinedload(Inventory.location))
            .where(Inventory.id == data.inventory_id)
        )
        if (
            existing_tx is None
            or target_inv is None
            or existing_tx.part_id != target_inv.part_id
            or existing_tx.location_id != target_inv.location_id
            or abs(existing_tx.quantity_change) != data.quantity
        ):
            raise AppHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The idempotency_key was already used with different parameters. "
                    "Use a new key for a different operation."
                ),
                code="idempotency_conflict",
                field="idempotency_key",
            )
        return _build_response(
            existing_tx, target_inv, existing_tx.part, existing_tx.location, user, idempotent_replay=True
        ), 200

    # ── 6. Notify every active admin ─────────────────────────────────────────
    admins = db.scalars(
        select(User).where(
            User.role == UserRole.STORE_ADMIN,
            User.is_active.is_(True),
        )
    ).all()

    notification_message = (
        f"{data.quantity} × {part.name} issued by "
        f"{user.employee_id} ({user.name}) at {loc.name}."
    )
    for admin in admins:
        db.add(
            Notification(
                recipient_user_id=admin.id,
                transaction_id=tx.id,
                message=notification_message,
            )
        )

    # ── 7. Commit ────────────────────────────────────────────────────────────
    db.commit()
    db.refresh(tx)

    return _build_response(tx, inv, part, loc, user, idempotent_replay=False), 201

