"""Automated tests for Admin Employee Management and Idempotent Demo-Data Seed."""
from sqlalchemy import func, select
from starlette import status

from app.core.security import verify_password
from app.models.enums import UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.spare_part import SparePart
from app.models.user import User
from app.scripts.seed_demo_data import DEMO_INVENTORY, run_seed
from tests.conftest import assert_ledger_invariant, create_location, create_user, login_as


# ============================================================================
# USER MANAGEMENT TESTS
# ============================================================================

def test_admin_create_user_success(client, db_session):
    """Admin can create a new employee who can log in immediately with Argon2 hash."""
    loc = create_location(db_session, code="HWD01", name="Haridwar Test Plant")
    create_user(db_session, employee_id="ADMIN01", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADMIN01")

    payload = {
        "employee_id": "emp1001",  # lowercase will be normalized to EMP1001
        "name": "Arun Sharma",
        "email": "Arun.Sharma@example.com",  # will be lowercased
        "role": "EMPLOYEE",
        "location_id": loc.id,
        "password": "SecurePassword123!",
    }

    resp = client.post("/api/admin/users", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()

    assert data["employee_id"] == "EMP1001"
    assert data["name"] == "Arun Sharma"
    assert data["email"] == "arun.sharma@example.com"
    assert data["role"] == "EMPLOYEE"
    assert data["location"]["id"] == loc.id
    assert data["is_active"] is True
    assert data["is_locked"] is False
    assert "password" not in data
    assert "password_hash" not in data

    # Verify Argon2id hash in database
    user_db = db_session.scalar(select(User).where(User.employee_id == "EMP1001"))
    assert user_db is not None
    assert user_db.password_hash.startswith("$argon2id$")
    assert verify_password("SecurePassword123!", user_db.password_hash)

    # Verify new user can log in immediately with both employee_id and email
    emp_token_resp1 = client.post(
        "/api/auth/login", json={"identifier": "EMP1001", "password": "SecurePassword123!"}
    )
    assert emp_token_resp1.status_code == 200, emp_token_resp1.text

    emp_token_resp2 = client.post(
        "/api/auth/login", json={"identifier": "arun.sharma@example.com", "password": "SecurePassword123!"}
    )
    assert emp_token_resp2.status_code == 200, emp_token_resp2.text


def test_create_user_validation_and_conflicts(client, db_session):
    """Validation: duplicate employee_id, duplicate email, invalid location, short password."""
    loc = create_location(db_session, code="BLR01")
    create_user(db_session, employee_id="ADMIN01", email="admin@example.com", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADMIN01")

    # 1. Duplicate employee_id -> 409
    resp = client.post(
        "/api/admin/users",
        json={
            "employee_id": "ADMIN01",
            "name": "Duplicate Admin",
            "email": "different@example.com",
            "location_id": loc.id,
            "password": "ValidPassword123!",
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["code"] == "duplicate_employee_id"
    assert resp.json()["field"] == "employee_id"

    # 2. Duplicate email -> 409
    resp = client.post(
        "/api/admin/users",
        json={
            "employee_id": "EMP9999",
            "name": "Different Name",
            "email": "admin@example.com",
            "location_id": loc.id,
            "password": "ValidPassword123!",
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["code"] == "duplicate_email"
    assert resp.json()["field"] == "email"

    # 3. Invalid location -> 422
    resp = client.post(
        "/api/admin/users",
        json={
            "employee_id": "EMP9999",
            "name": "Valid Name",
            "email": "unique@example.com",
            "location_id": 99999,
            "password": "ValidPassword123!",
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json()["code"] == "invalid_location"

    # 4. Short password (<12 chars) -> 422
    resp = client.post(
        "/api/admin/users",
        json={
            "employee_id": "EMP9999",
            "name": "Valid Name",
            "email": "unique@example.com",
            "location_id": loc.id,
            "password": "short",
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_user_update_and_demotion_protections(client, db_session):
    """Admin cannot demote self or last active admin; can update name and location."""
    loc1 = create_location(db_session, code="LOC1", name="Test Location 1")
    loc2 = create_location(db_session, code="LOC2", name="Test Location 2")
    admin = create_user(db_session, employee_id="ADMIN01", role=UserRole.STORE_ADMIN, location=loc1)
    headers = login_as(client, "ADMIN01")

    # 1. Admin cannot demote self
    resp = client.patch(
        f"/api/admin/users/{admin.id}",
        json={"role": "EMPLOYEE"},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["code"] == "self_action_forbidden"

    # 2. Add second admin
    admin2 = create_user(db_session, employee_id="ADMIN02", role=UserRole.STORE_ADMIN, location=loc1)

    # 3. Can update second admin's name and location
    resp = client.patch(
        f"/api/admin/users/{admin2.id}",
        json={"name": "Updated Admin 2", "location_id": loc2.id},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Admin 2"
    assert resp.json()["location"]["id"] == loc2.id

    # 4. Admin 1 can demote Admin 2 since Admin 1 is still active
    resp = client.patch(
        f"/api/admin/users/{admin2.id}",
        json={"role": "EMPLOYEE"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "EMPLOYEE"


def test_deactivate_and_activate_protections(client, db_session):
    """Self-deactivation and last-admin deactivation are blocked; deactivated user cannot log in."""
    loc = create_location(db_session)
    admin = create_user(db_session, employee_id="ADMIN01", role=UserRole.STORE_ADMIN, location=loc)
    emp = create_user(db_session, employee_id="EMP01", role=UserRole.EMPLOYEE, location=loc)
    headers = login_as(client, "ADMIN01")

    # 1. Self-deactivate blocked -> 409
    resp = client.post(f"/api/admin/users/{admin.id}/deactivate", headers=headers)
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["code"] == "self_action_forbidden"

    # 2. Deactivate employee succeeds
    resp = client.post(f"/api/admin/users/{emp.id}/deactivate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # 3. Deactivated employee cannot log in (401)
    login_resp = client.post("/api/auth/login", json={"identifier": "EMP01", "password": "TestPassword123!"})
    assert login_resp.status_code == 401

    # 4. Reactivate employee succeeds
    resp = client.post(f"/api/admin/users/{emp.id}/activate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    # 5. Reactivated employee can log in again
    login_resp = client.post("/api/auth/login", json={"identifier": "EMP01", "password": "TestPassword123!"})
    assert login_resp.status_code == 200


def test_reset_password_and_lockout_clearing(client, db_session):
    """Admin reset-password unlocks locked account and enables immediate login with new credentials."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="ADMIN01", role=UserRole.STORE_ADMIN, location=loc)
    emp = create_user(db_session, employee_id="EMP_LOCKED", role=UserRole.EMPLOYEE, location=loc)
    admin_headers = login_as(client, "ADMIN01")

    # Trigger lockout by 5 consecutive wrong passwords
    for _ in range(5):
        client.post("/api/auth/login", json={"identifier": "EMP_LOCKED", "password": "WrongPassword!"})

    # Account should now be locked (429)
    locked_resp = client.post("/api/auth/login", json={"identifier": "EMP_LOCKED", "password": "TestPassword123!"})
    assert locked_resp.status_code == 429

    # Admin resets password
    reset_resp = client.post(
        f"/api/admin/users/{emp.id}/reset-password",
        json={"password": "NewRecoveredPass123!"},
        headers=admin_headers,
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["is_locked"] is False

    # Employee can now log in immediately with the new password
    success_resp = client.post(
        "/api/auth/login",
        json={"identifier": "EMP_LOCKED", "password": "NewRecoveredPass123!"},
    )
    assert success_resp.status_code == 200


def test_admin_user_routes_permissions(client, db_session):
    """Unauthenticated gets 401; Employee gets 403 on all /api/admin/users routes."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_TEST", role=UserRole.EMPLOYEE, location=loc)
    emp_headers = login_as(client, "EMP_TEST")

    routes = [
        ("GET", "/api/admin/users"),
        ("POST", "/api/admin/users"),
        ("PATCH", "/api/admin/users/1"),
        ("POST", "/api/admin/users/1/deactivate"),
        ("POST", "/api/admin/users/1/activate"),
        ("POST", "/api/admin/users/1/reset-password"),
    ]

    for method, path in routes:
        # Unauthenticated -> 401
        r_unauth = client.request(method, path)
        assert r_unauth.status_code == 401, f"{method} {path} allowed without auth"

        # Employee -> 403
        r_emp = client.request(method, path, headers=emp_headers)
        assert r_emp.status_code == 403, f"{method} {path} allowed employee access"


# ============================================================================
# IDEMPOTENT DEMO SEED TESTS
# ============================================================================

def test_seed_demo_data_idempotency_and_ledger(db_session):
    """Run seed twice: first run creates records and transactions; second run skips all; ledger holds."""
    # Create required STORE_ADMIN user before running seed
    loc_seed = create_location(db_session, code="BLR", name="ITC Bengaluru", city="Bengaluru")
    create_user(db_session, employee_id="ADM001", role=UserRole.STORE_ADMIN, location=loc_seed)

    # ── First Run ────────────────────────────────────────────────────────────
    stats1 = run_seed(db_session, dry_run=False)
    assert stats1["locations_created"] > 0
    assert stats1["locations_skipped"] >= 1  # BLR was pre-existing and skipped!
    assert stats1["machines_created"] == 10
    assert stats1["parts_created"] == 14
    assert stats1["inventory_created"] > 0
    assert stats1["transactions_created"] > 0

    # Verify ledger invariant
    assert_ledger_invariant(db_session)

    # Check key demo parts exist with exact stock
    hwd_loc = db_session.scalar(select(Location).where(func.lower(Location.code) == "hwd"))
    assert hwd_loc is not None
    assert hwd_loc.name == "ITC Haridwar"

    brg_part = db_session.scalar(select(SparePart).where(SparePart.part_number == "BRG-6205"))
    assert brg_part is not None
    assert brg_part.category == "Bearing"

    brg_hwd_inv = db_session.scalar(
        select(Inventory).where(Inventory.part_id == brg_part.id, Inventory.location_id == hwd_loc.id)
    )
    assert brg_hwd_inv is not None
    assert brg_hwd_inv.quantity == 12
    assert brg_hwd_inv.store_name == "Mechanical Store"
    assert brg_hwd_inv.rack == "R14"
    assert brg_hwd_inv.bin == "B07"

    # Check opening transaction for BRG-6205
    brg_tx = db_session.scalar(
        select(InventoryTransaction).where(
            InventoryTransaction.part_id == brg_part.id,
            InventoryTransaction.location_id == hwd_loc.id,
        )
    )
    assert brg_tx is not None
    assert brg_tx.quantity_change == 12
    assert brg_tx.quantity_after == 12
    assert brg_tx.notes == "Opening stock (demo data)"

    # Check zero-stock item (MTR-1HP at Haridwar has quantity 0, NO transaction)
    mtr_part = db_session.scalar(select(SparePart).where(SparePart.part_number == "MTR-1HP"))
    assert mtr_part is not None
    mtr_hwd_inv = db_session.scalar(
        select(Inventory).where(Inventory.part_id == mtr_part.id, Inventory.location_id == hwd_loc.id)
    )
    assert mtr_hwd_inv is not None
    assert mtr_hwd_inv.quantity == 0

    mtr_tx = db_session.scalar(
        select(InventoryTransaction).where(
            InventoryTransaction.part_id == mtr_part.id,
            InventoryTransaction.location_id == hwd_loc.id,
        )
    )
    assert mtr_tx is None  # Consistent: 0 transactions for quantity 0

    # ── Second Run (Must skip all without error or duplication) ───────────────
    stats2 = run_seed(db_session, dry_run=False)
    assert stats2["locations_created"] == 0
    assert stats2["machines_created"] == 0
    assert stats2["parts_created"] == 0
    assert stats2["links_created"] == 0
    assert stats2["inventory_created"] == 0
    assert stats2["transactions_created"] == 0

    assert stats2["locations_skipped"] >= 2
    assert stats2["machines_skipped"] == 10
    assert stats2["parts_skipped"] == 14
    assert stats2["inventory_skipped"] == len(DEMO_INVENTORY)

    # Invariant still holds perfectly after second run
    assert_ledger_invariant(db_session)
