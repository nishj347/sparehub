"""Tests for the issue part workflow: stock deductions, notifications, idempotency, rollbacks."""
import pytest
from app.models.enums import TransactionType, UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.notification import Notification
from tests.conftest import (
    assert_ledger_invariant,
    create_inventory,
    create_location,
    create_part,
    create_user,
    login_as,
)


def test_issue_success_deducts_stock_records_ledger_and_notifies_admins(client, db_session):
    loc = create_location(db_session)
    admin1 = create_user(db_session, employee_id="ADM_NOTIF1", role=UserRole.STORE_ADMIN, location=loc)
    admin2 = create_user(db_session, employee_id="ADM_NOTIF2", role=UserRole.STORE_ADMIN, location=loc)
    inactive_admin = create_user(db_session, employee_id="ADM_NOTIF3", role=UserRole.STORE_ADMIN, is_active=False, location=loc)
    emp = create_user(db_session, employee_id="EMP_ISSUE1", role=UserRole.EMPLOYEE, location=loc)

    headers = login_as(client, "EMP_ISSUE1")
    part = create_part(db_session, part_number="P-ISS-01", name="Air Filter")
    inv = create_inventory(db_session, part, loc, quantity=10, min_stock_level=2, user=admin1)

    payload = {
        "inventory_id": inv.id,
        "quantity": 3,
        "idempotency_key": "unique-idem-key-001",
        "notes": "Replacing worn filter",
    }

    resp = client.post("/api/issues", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["quantity_issued"] == 3
    assert data["quantity_remaining"] == 7
    assert data["idempotent_replay"] is False
    assert data["employee"]["employee_id"] == "EMP_ISSUE1"

    # Check inventory
    db_session.refresh(inv)
    assert inv.quantity == 7

    # Check ledger transaction
    tx = (
        db_session.query(InventoryTransaction)
        .filter_by(part_id=part.id, location_id=loc.id)
        .order_by(InventoryTransaction.id.desc())
        .first()
    )
    assert tx.transaction_type == TransactionType.ISSUED
    assert tx.quantity_change == -3
    assert tx.quantity_after == 7
    assert tx.user_id == emp.id

    # Check notifications: created for active admins only
    notifs = db_session.query(Notification).all()
    assert len(notifs) == 2
    recipient_ids = {n.recipient_user_id for n in notifs}
    assert recipient_ids == {admin1.id, admin2.id}
    assert inactive_admin.id not in recipient_ids

    assert_ledger_invariant(db_session)


def test_issue_insufficient_and_zero_stock_fails(client, db_session):
    loc = create_location(db_session)
    admin = create_user(db_session, employee_id="ADM_ISS_STK", role=UserRole.STORE_ADMIN, location=loc)
    create_user(db_session, employee_id="EMP_ISSUE2", role=UserRole.EMPLOYEE, location=loc)
    headers = login_as(client, "EMP_ISSUE2")

    part = create_part(db_session, part_number="P-ISS-02")
    inv = create_inventory(db_session, part, loc, quantity=3, user=admin)

    # 1. Insufficient stock (requested 5, available 3)
    resp = client.post(
        "/api/issues",
        json={"inventory_id": inv.id, "quantity": 5, "idempotency_key": "key-insufficient-01"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "insufficient_stock"

    # 2. Zero stock
    inv.quantity = 0
    db_session.commit()
    resp_zero = client.post(
        "/api/issues",
        json={"inventory_id": inv.id, "quantity": 1, "idempotency_key": "key-zero-stock-01"},
        headers=headers,
    )
    assert resp_zero.status_code == 409
    assert resp_zero.json()["code"] == "insufficient_stock"


def test_issue_inactive_part_and_inactive_location_fails(client, db_session):
    active_loc = create_location(db_session, name="Active Loc", code="ALOC1")
    inactive_loc = create_location(db_session, name="Inactive Loc", code="ILOC1", is_active=False)
    create_user(db_session, employee_id="EMP_ISSUE3", role=UserRole.EMPLOYEE, location=active_loc)
    headers = login_as(client, "EMP_ISSUE3")

    # Inactive part
    inactive_part = create_part(db_session, part_number="P-INACTIVE", is_active=False)
    inv1 = create_inventory(db_session, inactive_part, active_loc, quantity=5)

    resp_part = client.post(
        "/api/issues",
        json={"inventory_id": inv1.id, "quantity": 1, "idempotency_key": "key-inactive-part"},
        headers=headers,
    )
    assert resp_part.status_code == 409
    assert resp_part.json()["code"] == "part_inactive"

    # Inactive location
    active_part = create_part(db_session, part_number="P-ACTIVE")
    inv2 = create_inventory(db_session, active_part, inactive_loc, quantity=5)

    resp_loc = client.post(
        "/api/issues",
        json={"inventory_id": inv2.id, "quantity": 1, "idempotency_key": "key-inactive-loc"},
        headers=headers,
    )
    assert resp_loc.status_code == 409
    assert resp_loc.json()["code"] == "location_inactive"


def test_identity_taken_from_token_not_payload(client, db_session):
    """Caller cannot forge user identity via body payload."""
    loc = create_location(db_session)
    victim = create_user(db_session, employee_id="VICTIM01", role=UserRole.EMPLOYEE, location=loc)
    attacker = create_user(db_session, employee_id="ATTACKER01", role=UserRole.EMPLOYEE, location=loc)
    headers = login_as(client, "ATTACKER01")

    part = create_part(db_session, part_number="P-FORGE-01")
    inv = create_inventory(db_session, part, loc, quantity=10)

    # Attempt to pass victim's ID in body
    payload = {
        "inventory_id": inv.id,
        "quantity": 2,
        "idempotency_key": "key-forge-attempt",
        "user_id": victim.id,
        "employee_id": victim.employee_id,
    }
    resp = client.post("/api/issues", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()

    # The returned employee identity MUST be attacker, not victim
    assert data["employee"]["employee_id"] == "ATTACKER01"

    # In DB, transaction user_id must be attacker
    tx = db_session.query(InventoryTransaction).filter_by(idempotency_key="key-forge-attempt").first()
    assert tx.user_id == attacker.id


def test_idempotent_replay_and_parameter_conflict(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_IDEM", role=UserRole.EMPLOYEE, location=loc)
    headers = login_as(client, "EMP_IDEM")

    part = create_part(db_session, part_number="P-IDEM-01")
    inv = create_inventory(db_session, part, loc, quantity=10)

    # 1. First execution
    payload = {"inventory_id": inv.id, "quantity": 2, "idempotency_key": "idem-key-stable-123"}
    resp1 = client.post("/api/issues", json=payload, headers=headers)
    assert resp1.status_code == 201
    assert resp1.json()["idempotent_replay"] is False
    assert resp1.json()["quantity_remaining"] == 8

    # 2. Replay with identical parameters: should return same result without additional stock deduction
    resp2 = client.post("/api/issues", json=payload, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["idempotent_replay"] is True
    assert resp2.json()["quantity_remaining"] == 8

    db_session.refresh(inv)
    assert inv.quantity == 8  # Only 2 units deducted, not 4!

    # 3. Same key with different quantity -> 409 Conflict
    conflict_payload = {"inventory_id": inv.id, "quantity": 5, "idempotency_key": "idem-key-stable-123"}
    resp_conflict = client.post("/api/issues", json=conflict_payload, headers=headers)
    assert resp_conflict.status_code == 409
    assert resp_conflict.json()["code"] == "idempotency_conflict"

    assert_ledger_invariant(db_session)


def test_issue_by_part_and_location_or_missing_target(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_ISS_RESOLV", location=loc)
    headers = login_as(client, "EMP_ISS_RESOLV")

    part = create_part(db_session, part_number="P-RESOLV-01")
    inv = create_inventory(db_session, part, loc, quantity=10)

    # 1. Resolve from part_id and location_id
    resp = client.post(
        "/api/issues",
        json={"part_id": part.id, "location_id": loc.id, "quantity": 2, "idempotency_key": "resolve-by-ids-01"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["quantity_remaining"] == 8

    # 2. Neither provided
    resp_empty = client.post(
        "/api/issues",
        json={"quantity": 1, "idempotency_key": "neither-provided-01"},
        headers=headers,
    )
    assert resp_empty.status_code == 422
    assert resp_empty.json()["code"] == "validation_error"

    # 3. Non-existent inventory_id
    resp_nf = client.post(
        "/api/issues",
        json={"inventory_id": 999999, "quantity": 1, "idempotency_key": "not-found-inv-01"},
        headers=headers,
    )
    assert resp_nf.status_code == 404
    assert resp_nf.json()["code"] == "not_found"

    assert_ledger_invariant(db_session)


def test_forced_failure_rolls_back_stock_and_ledger(client, db_session, monkeypatch):
    """If an error occurs during issue processing, all changes (stock, ledger) must roll back atomically."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="ADM_RB", role=UserRole.STORE_ADMIN, location=loc)
    create_user(db_session, employee_id="EMP_RB", role=UserRole.EMPLOYEE, location=loc)
    headers = login_as(client, "EMP_RB")

    part = create_part(db_session, part_number="P-RB-01")
    inv = create_inventory(db_session, part, loc, quantity=10)

    # Monkeypatch Notification init to simulate failure during notification insertion
    def fail_init(*args, **kwargs):
        raise RuntimeError("Simulated notification service failure")

    monkeypatch.setattr(Notification, "__init__", fail_init)

    payload = {"inventory_id": inv.id, "quantity": 4, "idempotency_key": "rollback-test-key-01"}
    with pytest.raises(Exception):
        client.post("/api/issues", json=payload, headers=headers)

    # Verify rollback: stock remains 10, no issue ledger row was saved
    db_session.expire_all()
    db_session.refresh(inv)
    assert inv.quantity == 10
    issue_tx = db_session.query(InventoryTransaction).filter_by(idempotency_key="rollback-test-key-01").first()
    assert issue_tx is None
    notifs = db_session.query(Notification).all()
    assert len(notifs) == 0

    assert_ledger_invariant(db_session)
