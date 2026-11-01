"""Tests for inventory operations: receive, adjust, ledger invariant, and image validation."""
import io
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


def test_create_part_with_initial_stock_and_receive_ledger(client, db_session):
    loc = create_location(db_session)
    admin = create_user(db_session, employee_id="ADM_INV1", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADM_INV1")

    # 1. Create part
    part = create_part(db_session, part_number="P-INV-01", name="Hydraulic Valve")
    inv = create_inventory(db_session, part, loc, quantity=10, min_stock_level=3, user=admin)

    # 2. Receive stock (+15)
    resp = client.post(
        f"/api/admin/inventory/{inv.id}/receive",
        json={"quantity": 15, "notes": "Batch shipment #101"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["quantity"] == 25

    # Check ledger transaction
    db_session.refresh(inv)
    latest_tx = (
        db_session.query(InventoryTransaction)
        .filter_by(part_id=part.id, location_id=loc.id)
        .order_by(InventoryTransaction.id.desc())
        .first()
    )
    assert latest_tx is not None
    assert latest_tx.transaction_type == TransactionType.RECEIVED
    assert latest_tx.quantity_change == 15
    assert latest_tx.quantity_after == 25
    assert latest_tx.notes == "Batch shipment #101"

    assert_ledger_invariant(db_session)


def test_adjust_stock_positive_and_negative_delta(client, db_session):
    loc = create_location(db_session)
    admin = create_user(db_session, employee_id="ADM_INV2", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADM_INV2")

    part = create_part(db_session, part_number="P-INV-02", name="O-Ring Seal")
    inv = create_inventory(db_session, part, loc, quantity=20, min_stock_level=5, user=admin)

    # Adjust downwards: 20 -> 14 (delta = -6)
    resp_down = client.post(
        f"/api/admin/inventory/{inv.id}/adjust",
        json={"new_quantity": 14, "notes": "Damage during audit"},
        headers=headers,
    )
    assert resp_down.status_code == 200
    assert resp_down.json()["quantity"] == 14

    tx_down = (
        db_session.query(InventoryTransaction)
        .filter_by(part_id=part.id, location_id=loc.id)
        .order_by(InventoryTransaction.id.desc())
        .first()
    )
    assert tx_down.transaction_type == TransactionType.ADJUSTED
    assert tx_down.quantity_change == -6
    assert tx_down.quantity_after == 14

    assert_ledger_invariant(db_session)

    # Adjust upwards: 14 -> 30 (delta = +16)
    resp_up = client.post(
        f"/api/admin/inventory/{inv.id}/adjust",
        json={"new_quantity": 30, "notes": "Found uncatalogued crate"},
        headers=headers,
    )
    assert resp_up.status_code == 200
    assert resp_up.json()["quantity"] == 30

    tx_up = (
        db_session.query(InventoryTransaction)
        .filter_by(part_id=part.id, location_id=loc.id)
        .order_by(InventoryTransaction.id.desc())
        .first()
    )
    assert tx_up.transaction_type == TransactionType.ADJUSTED
    assert tx_up.quantity_change == 16
    assert tx_up.quantity_after == 30

    assert_ledger_invariant(db_session)


def test_adjust_with_same_quantity_gives_422(client, db_session):
    loc = create_location(db_session)
    admin = create_user(db_session, employee_id="ADM_INV3", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADM_INV3")

    part = create_part(db_session, part_number="P-INV-03")
    inv = create_inventory(db_session, part, loc, quantity=10, user=admin)

    resp = client.post(
        f"/api/admin/inventory/{inv.id}/adjust",
        json={"new_quantity": 10, "notes": "No physical change"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "no_change"

    assert_ledger_invariant(db_session)


def test_receive_on_inactive_part_gives_409(client, db_session):
    loc = create_location(db_session)
    admin = create_user(db_session, employee_id="ADM_INV4", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADM_INV4")

    part = create_part(db_session, part_number="P-INV-04", is_active=False)
    inv = create_inventory(db_session, part, loc, quantity=0, user=admin)

    resp = client.post(
        f"/api/admin/inventory/{inv.id}/receive",
        json={"quantity": 5, "notes": "Trying to receive inactive"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "part_inactive"

    assert_ledger_invariant(db_session)


def test_image_upload_validations(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="ADM_INV5", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADM_INV5")
    part = create_part(db_session, part_number="P-INV-05")

    # 1. Renamed .txt file disguised as .jpg
    fake_txt = io.BytesIO(b"This is purely plaintext and not a JPEG or PNG!")
    resp_txt = client.post(
        f"/api/admin/parts/{part.id}/image",
        files={"file": ("photo.jpg", fake_txt, "image/jpeg")},
        headers=headers,
    )
    assert resp_txt.status_code == 422
    assert resp_txt.json()["code"] == "invalid_image"

    # 2. SVG file
    svg_data = io.BytesIO(b"<svg xmlns='http://www.w3.org/2000/svg'><circle r='5'/></svg>")
    resp_svg = client.post(
        f"/api/admin/parts/{part.id}/image",
        files={"file": ("vector.svg", svg_data, "image/svg+xml")},
        headers=headers,
    )
    assert resp_svg.status_code == 422
    assert resp_svg.json()["code"] == "invalid_image"

    # 3. Oversize file (> 5MB)
    oversize_data = io.BytesIO(b"\xff\xd8\xff" + b"0" * (6 * 1024 * 1024))
    resp_oversize = client.post(
        f"/api/admin/parts/{part.id}/image",
        files={"file": ("huge.jpg", oversize_data, "image/jpeg")},
        headers=headers,
    )
    assert resp_oversize.status_code == 413


def test_inventory_update_coordinates_and_add_location(client, db_session):
    loc1 = create_location(db_session, name="Plant 1", code="PLT01")
    loc2 = create_location(db_session, name="Plant 2", code="PLT02")
    admin = create_user(db_session, employee_id="ADM_INV_COORD", role=UserRole.STORE_ADMIN, location=loc1)
    headers = login_as(client, "ADM_INV_COORD")

    part = create_part(db_session, part_number="P-COORD-01")
    inv = create_inventory(db_session, part, loc1, quantity=10, min_stock_level=2)

    # 1. Update coordinates
    resp_update = client.patch(
        f"/api/admin/inventory/{inv.id}",
        json={"store_name": "Bay A", "rack": "R-10", "bin": "B-22", "min_stock_level": 5},
        headers=headers,
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["rack"] == "R-10"
    assert resp_update.json()["bin"] == "B-22"

    # 2. Add part to new location with initial stock
    resp_add = client.post(
        f"/api/admin/parts/{part.id}/inventory",
        json={"location_id": loc2.id, "quantity": 8, "store_name": "Store B", "min_stock_level": 2},
        headers=headers,
    )
    assert resp_add.status_code == 201
    assert resp_add.json()["quantity"] == 8

    assert_ledger_invariant(db_session)
