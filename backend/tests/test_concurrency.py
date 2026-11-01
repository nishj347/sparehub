"""Concurrency tests with real threads and real database row-level locking."""
import concurrent.futures
import pytest
from app.models.enums import TransactionType, UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from tests.conftest import (
    assert_ledger_invariant,
    create_inventory,
    create_location,
    create_part,
    create_user,
    login_as,
)


@pytest.mark.concurrency
def test_concurrent_issues_stock_depletion(client, db_session):
    """10 simultaneous issues of 1 unit against stock 5: exactly 5 succeed, 5 get insufficient_stock."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="ADM_CC1", role=UserRole.STORE_ADMIN, location=loc)
    create_user(db_session, employee_id="EMP_CC1", role=UserRole.EMPLOYEE, location=loc)
    headers = login_as(client, "EMP_CC1")

    part = create_part(db_session, part_number="P-CC-01")
    inv = create_inventory(db_session, part, loc, quantity=5)
    inv_id = inv.id
    part_id = part.id
    loc_id = loc.id

    def do_issue(idx: int):
        payload = {
            "inventory_id": inv_id,
            "quantity": 1,
            "idempotency_key": f"concurrent-issue-{idx}",
        }
        return client.post("/api/issues", json=payload, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(do_issue, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    successes = [r for r in results if r.status_code in {200, 201}]
    conflicts = [r for r in results if r.status_code == 409]

    assert len(successes) == 5, f"Expected 5 successes, got {len(successes)}"
    assert len(conflicts) == 5, f"Expected 5 conflicts, got {len(conflicts)}"
    for c in conflicts:
        assert c.json()["code"] == "insufficient_stock"

    db_session.expire_all()
    db_session.refresh(inv)
    assert inv.quantity == 0

    issue_txs = (
        db_session.query(InventoryTransaction)
        .filter_by(part_id=part_id, location_id=loc_id, transaction_type=TransactionType.ISSUED)
        .all()
    )
    assert len(issue_txs) == 5

    assert_ledger_invariant(db_session)


@pytest.mark.concurrency
def test_concurrent_issues_same_idempotency_key(client, db_session):
    """10 simultaneous requests with the SAME idempotency key: exactly one deduction."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_CC2", role=UserRole.EMPLOYEE, location=loc)
    headers = login_as(client, "EMP_CC2")

    part = create_part(db_session, part_number="P-CC-02")
    inv = create_inventory(db_session, part, loc, quantity=10)
    inv_id = inv.id

    shared_key = "concurrent-same-idempotency-key-xyz"

    def do_issue(_: int):
        payload = {
            "inventory_id": inv_id,
            "quantity": 2,
            "idempotency_key": shared_key,
        }
        return client.post("/api/issues", json=payload, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(do_issue, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All should return 200 or 201 (either original or replay)
    for r in results:
        assert r.status_code in {200, 201}

    db_session.expire_all()
    db_session.refresh(inv)
    assert inv.quantity == 8  # Only 2 units deducted in total

    txs = db_session.query(InventoryTransaction).filter_by(idempotency_key=shared_key).all()
    assert len(txs) == 1

    assert_ledger_invariant(db_session)


@pytest.mark.concurrency
def test_concurrent_receives_sum_correctly(client, db_session):
    """10 simultaneous receives of +1 give exactly +10."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="ADM_CC3", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADM_CC3")

    part = create_part(db_session, part_number="P-CC-03")
    inv = create_inventory(db_session, part, loc, quantity=0)
    inv_id = inv.id
    part_id = part.id
    loc_id = loc.id

    def do_receive(idx: int):
        return client.post(
            f"/api/admin/inventory/{inv_id}/receive",
            json={"quantity": 1, "notes": f"Concurrent batch #{idx}"},
            headers=headers,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(do_receive, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for r in results:
        assert r.status_code == 200

    db_session.expire_all()
    db_session.refresh(inv)
    assert inv.quantity == 10

    receive_txs = (
        db_session.query(InventoryTransaction)
        .filter_by(part_id=part_id, location_id=loc_id, transaction_type=TransactionType.RECEIVED)
        .all()
    )
    assert len(receive_txs) == 10

    assert_ledger_invariant(db_session)


@pytest.mark.concurrency
def test_concurrent_mixed_issues_and_receives(client, db_session):
    """Mixed concurrent issues and receives maintain ledger invariant."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="ADM_CC4", role=UserRole.STORE_ADMIN, location=loc)
    create_user(db_session, employee_id="EMP_CC4", role=UserRole.EMPLOYEE, location=loc)
    admin_headers = login_as(client, "ADM_CC4")
    emp_headers = login_as(client, "EMP_CC4")

    part = create_part(db_session, part_number="P-CC-04")
    inv = create_inventory(db_session, part, loc, quantity=20)
    inv_id = inv.id

    def worker(i: int):
        if i % 2 == 0:
            # Issue 1
            return client.post(
                "/api/issues",
                json={"inventory_id": inv_id, "quantity": 1, "idempotency_key": f"mixed-issue-{i}"},
                headers=emp_headers,
            )
        else:
            # Receive 2
            return client.post(
                f"/api/admin/inventory/{inv_id}/receive",
                json={"quantity": 2, "notes": f"Mixed receive {i}"},
                headers=admin_headers,
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All should succeed since stock never drops to 0
    for r in results:
        assert r.status_code in {200, 201}

    db_session.expire_all()
    assert_ledger_invariant(db_session)
