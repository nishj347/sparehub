"""Verification script for database constraints and query consistency.

Tests:
1. Database constraints reject invalid data (7 integrity tests inside rolled-back savepoints)
2. Query check for BRG-6205 across spare_parts -> inventory -> locations
3. Transaction ledger history for BRG-6205 at ITC Bengaluru
"""

import os
import sys
from typing import Callable, List, Tuple

# Ensure backend root directory is on the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, text

from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import TransactionType, UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.spare_part import SparePart
from app.models.user import User


def test_rejection(
    session: Session,
    test_name: str,
    action: Callable[[Session], None],
) -> Tuple[bool, str]:
    """Execute an invalid DB operation inside a savepoint and verify it is rejected."""
    sp = session.begin_nested()
    try:
        action(session)
        session.flush()
        sp.rollback()
        return False, "ERROR: Expected database rejection, but operation succeeded!"
    except (IntegrityError, DBAPIError) as exc:
        sp.rollback()
        # Extract underlying DB error message
        orig_msg = str(getattr(exc, "orig", exc))
        first_line = orig_msg.strip().split("\n")[0]
        return True, first_line


def run_constraint_verification(session: Session) -> None:
    """Verify that PostgreSQL rejects each invalid data condition."""
    print("\n" + "=" * 70)
    print("1. DATABASE INTEGRITY CONSTRAINT REJECTION TESTS")
    print("=" * 70)

    # Get valid reference IDs
    part = session.scalars(select(SparePart)).first()
    loc = session.scalars(select(Location)).first()
    user = session.scalars(select(User)).first()

    assert part is not None and loc is not None and user is not None

    tests = [
        (
            "Inventory with negative quantity",
            lambda s: s.add(
                Inventory(
                    part_id=part.id,
                    location_id=loc.id,
                    quantity=-5,
                    min_stock_level=0,
                )
            ),
        ),
        (
            "Duplicate inventory row for same (part_id, location_id)",
            lambda s: s.add(
                Inventory(
                    part_id=part.id,
                    location_id=loc.id,
                    quantity=10,
                    min_stock_level=0,
                )
            ),
        ),
        (
            "ISSUED transaction with positive quantity_change",
            lambda s: s.add(
                InventoryTransaction(
                    part_id=part.id,
                    location_id=loc.id,
                    user_id=user.id,
                    transaction_type=TransactionType.ISSUED,
                    quantity_change=5,
                    quantity_after=15,
                )
            ),
        ),
        (
            "RECEIVED transaction with negative quantity_change",
            lambda s: s.add(
                InventoryTransaction(
                    part_id=part.id,
                    location_id=loc.id,
                    user_id=user.id,
                    transaction_type=TransactionType.RECEIVED,
                    quantity_change=-5,
                    quantity_after=5,
                )
            ),
        ),
        (
            "Transaction with quantity_change = 0",
            lambda s: s.add(
                InventoryTransaction(
                    part_id=part.id,
                    location_id=loc.id,
                    user_id=user.id,
                    transaction_type=TransactionType.ADJUSTED,
                    quantity_change=0,
                    quantity_after=10,
                )
            ),
        ),
        (
            "Duplicate spare_parts.part_number",
            lambda s: s.add(
                SparePart(
                    part_number="BRG-6205",
                    name="Duplicate Bearing",
                    category="Bearing",
                )
            ),
        ),
        (
            "Duplicate users.employee_id",
            lambda s: s.add(
                User(
                    employee_id="ITCADM001",
                    name="Duplicate Admin",
                    email="duplicate.admin@example-itc.test",
                    password_hash="dummy_hash",
                    role=UserRole.STORE_ADMIN,
                    location_id=loc.id,
                )
            ),
        ),
    ]

    all_passed = True
    for idx, (name, action) in enumerate(tests, start=1):
        rejected, detail = test_rejection(session, name, action)
        status_str = "[REJECTED AS EXPECTED]" if rejected else "[FAILED]"
        print(f"\nTest 5.{idx}: {name}")
        print(f"Status: {status_str}")
        print(f"Database Error: {detail}")
        if not rejected:
            all_passed = False

    if not all_passed:
        raise RuntimeError("One or more constraint tests failed!")


def run_query_check(session: Session) -> None:
    """Run Query check for BRG-6205 and its ledger history."""
    print("\n" + "=" * 70)
    print("2. QUERY CHECK: BRG-6205 INVENTORY & LOCATIONS")
    print("=" * 70)

    part = session.scalars(
        select(SparePart).where(SparePart.part_number == "BRG-6205")
    ).first()
    if not part:
        raise ValueError("BRG-6205 not found in database!")

    inv_records = session.execute(
        select(Location.city, Location.code, Inventory.quantity, Inventory.store_name, Inventory.rack, Inventory.bin)
        .join(Inventory, Inventory.location_id == Location.id)
        .where(Inventory.part_id == part.id)
        .order_by(Location.code.asc())
    ).all()

    print(f"Part: {part.part_number} — {part.name} ({part.manufacturer})")
    print("-" * 70)
    print(f"{'Location City':<18} {'Code':<6} {'Qty':<6} {'Store':<20} {'Rack':<6} {'Bin':<6}")
    print("-" * 70)
    for rec in inv_records:
        print(f"{rec.city:<18} {rec.code:<6} {rec.quantity:<6} {rec.store_name or '-':<20} {rec.rack or '-':<6} {rec.bin or '-':<6}")

    print("\n" + "=" * 70)
    print("3. BENGALURU LEDGER HISTORY FOR BRG-6205")
    print("=" * 70)

    blr_loc = session.scalars(select(Location).where(Location.code == "BLR")).first()
    assert blr_loc is not None

    txs = session.execute(
        select(
            InventoryTransaction.id,
            InventoryTransaction.transaction_type,
            InventoryTransaction.quantity_change,
            InventoryTransaction.quantity_after,
            User.employee_id,
            User.name,
            InventoryTransaction.created_at,
            InventoryTransaction.notes,
        )
        .outerjoin(User, InventoryTransaction.user_id == User.id)
        .where(
            InventoryTransaction.part_id == part.id,
            InventoryTransaction.location_id == blr_loc.id,
        )
        .order_by(InventoryTransaction.created_at.asc(), InventoryTransaction.id.asc())
    ).all()

    print(f"{'Tx ID':<7} {'Type':<10} {'Change':<8} {'After':<7} {'Actor ID':<12} {'Notes'}")
    print("-" * 70)
    for t in txs:
        change_str = f"+{t.quantity_change}" if t.quantity_change > 0 else str(t.quantity_change)
        actor_str = f"{t.employee_id} ({t.name})" if t.employee_id else "SYSTEM"
        print(f"{t.id:<7} {t.transaction_type.value:<10} {change_str:<8} {t.quantity_after:<7} {actor_str:<12} {t.notes or ''}")


def main() -> None:
    session = SessionLocal()
    try:
        run_constraint_verification(session)
        run_query_check(session)
        print("\n" + "=" * 70)
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
        print("=" * 70 + "\n")
    finally:
        session.close()


if __name__ == "__main__":
    main()
