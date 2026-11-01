"""Tests for employee-facing part search, filters, wildcard escaping, and permissions."""
import pytest
from app.models.enums import UserRole
from app.models.part_machine import PartMachine
from tests.conftest import (
    create_inventory,
    create_location,
    create_machine,
    create_part,
    create_user,
    login_as,
)


def test_search_multi_term_and_logic(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_SRCH1", location=loc)
    headers = login_as(client, "EMP_SRCH1")

    # Seed 3 parts
    p1 = create_part(db_session, part_number="P-SKF-01", name="Deep Groove Ball Bearing", manufacturer="SKF", category="Bearings")
    p2 = create_part(db_session, part_number="P-TIM-01", name="Roller Bearing", manufacturer="Timken", category="Bearings")
    p3 = create_part(db_session, part_number="P-SKF-02", name="V-Belt Drive", manufacturer="SKF", category="Belts")

    create_inventory(db_session, p1, loc, quantity=5)
    create_inventory(db_session, p2, loc, quantity=5)
    create_inventory(db_session, p3, loc, quantity=5)

    # Search for "SKF Bearing" -> must match ONLY p1 (contains both terms)
    resp = client.get("/api/parts?q=SKF Bearing", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["part_number"] == "P-SKF-01"


def test_search_wildcard_escaping(client, db_session):
    """Wildcards % and _ should be escaped and not act as SQL pattern wildcards."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_SRCH2", location=loc)
    headers = login_as(client, "EMP_SRCH2")

    p1 = create_part(db_session, part_number="PRT-NORMAL", name="Standard Sensor")
    p2 = create_part(db_session, part_number="PRT-SPECIAL-100%", name="Tolerance 100% Sensor")

    create_inventory(db_session, p1, loc, quantity=5)
    create_inventory(db_session, p2, loc, quantity=5)

    # Searching "%" should only match the part with actual "%" literal in name/part_number
    resp = client.get("/api/parts?q=%", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    part_numbers = [item["part_number"] for item in items]
    assert "PRT-SPECIAL-100%" in part_numbers
    assert "PRT-NORMAL" not in part_numbers


def test_machine_filtering_and_association(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_SRCH3", location=loc)
    headers = login_as(client, "EMP_SRCH3")

    machine = create_machine(db_session, name="Stamping Press A", code="STAMP500", location=loc)
    other_machine = create_machine(db_session, name="Lathe B", code="LTH200", location=loc)

    p1 = create_part(db_session, part_number="P-MACH-01", name="Press Die Plate")
    p2 = create_part(db_session, part_number="P-MACH-02", name="Lathe Chuck")

    create_inventory(db_session, p1, loc, quantity=2)
    create_inventory(db_session, p2, loc, quantity=2)

    # Link p1 to stamping press
    link1 = PartMachine(part_id=p1.id, machine_id=machine.id)
    link2 = PartMachine(part_id=p2.id, machine_id=other_machine.id)
    db_session.add_all([link1, link2])
    db_session.commit()

    resp = client.get(f"/api/parts?machine_id={machine.id}", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["part_number"] == "P-MACH-01"


def test_inactive_records_excluded_from_public_search(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_SRCH4", location=loc)
    headers = login_as(client, "EMP_SRCH4")

    active_part = create_part(db_session, part_number="P-ACT-99", is_active=True)
    inactive_part = create_part(db_session, part_number="P-INACT-99", is_active=False)

    create_inventory(db_session, active_part, loc, quantity=10)
    create_inventory(db_session, inactive_part, loc, quantity=10)

    resp = client.get("/api/parts", headers=headers)
    assert resp.status_code == 200
    item_pns = [it["part_number"] for it in resp.json()["items"]]
    assert "P-ACT-99" in item_pns
    assert "P-INACT-99" not in item_pns


def test_primary_location_assigned_to_caller_location(client, db_session):
    loc1 = create_location(db_session, name="Pune Facility", code="PUN01")
    loc2 = create_location(db_session, name="Mumbai Facility", code="MUM01")

    # User assigned to Mumbai
    create_user(db_session, employee_id="EMP_MUMBAI", location=loc2)
    headers = login_as(client, "EMP_MUMBAI")

    part = create_part(db_session, part_number="P-LOC-TEST")
    create_inventory(db_session, part, loc1, quantity=15)
    create_inventory(db_session, part, loc2, quantity=7)

    resp = client.get("/api/parts", headers=headers)
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    # Primary location for Mumbai employee should be Mumbai
    assert item["primary_location"]["location"]["code"] == "MUM01"
    assert item["primary_location"]["is_my_location"] is True


def test_employee_response_hides_admin_fields(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_SEC_VIEW", location=loc)
    headers = login_as(client, "EMP_SEC_VIEW")

    part = create_part(db_session, part_number="P-CONFIDENTIAL")
    create_inventory(db_session, part, loc, quantity=10, min_stock_level=5)

    resp = client.get(f"/api/parts/{part.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Public schema must not expose min_stock_level or internal notes
    assert "min_stock_level" not in data
    assert "notes" not in data
