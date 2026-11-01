"""Automated tests for Surplus Material & Machinery (Module 12A)."""
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import func, select
from starlette import status

from app.models.enums import UserRole
from app.models.notification import Notification
from app.models.surplus import SurplusCondition, SurplusInterest, SurplusItem, SurplusKind, SurplusStatus
from tests.conftest import (
    TestingSessionLocal,
    create_location,
    create_part,
    create_user,
    login_as,
)


def create_surplus_item_db(
    db,
    admin,
    location,
    title="Surplus Conveyor Motor",
    kind=SurplusKind.MACHINERY,
    quantity=1,
    unit="units",
    condition=SurplusCondition.GOOD,
    status=SurplusStatus.AVAILABLE,
    valid_until=None,
    part=None,
    description="Surplus equipment in good working condition",
):
    item = SurplusItem(
        title=title,
        kind=kind.value,
        quantity=quantity,
        unit=unit,
        condition=condition.value,
        location_id=location.id,
        status=status.value,
        valid_until=valid_until,
        part_id=part.id if part else None,
        created_by=admin.id,
        description=description,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_surplus_create_and_validation(client, db_session):
    """Admin can create listings; input validation rules are enforced."""
    loc_active = create_location(db_session, code="LOC-ACT", name="Active Plant")
    loc_inactive = create_location(db_session, code="LOC-INACT", name="Inactive Plant", is_active=False)
    admin = create_user(db_session, employee_id="ADM_SR01", role=UserRole.STORE_ADMIN, location=loc_active)
    part = create_part(db_session, part_number="BRG-6205")
    headers = login_as(client, "ADM_SR01")

    # 1. Successful creation of machinery
    payload_mach = {
        "title": "Industrial Lathe Machine",
        "kind": "MACHINERY",
        "quantity": 1,
        "unit": "units",
        "condition": "GOOD",
        "location_id": loc_active.id,
        "description": "Functional precision lathe",
    }
    resp = client.post("/api/admin/surplus", json=payload_mach, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()
    assert data["title"] == "Industrial Lathe Machine"
    assert data["kind"] == "MACHINERY"
    assert data["status"] == "AVAILABLE"

    # 2. Successful creation of surplus spare part linked to BRG-6205
    payload_part = {
        "title": "Deep Groove Ball Bearing 6205",
        "kind": "SPARE_PART",
        "quantity": 25,
        "unit": "pieces",
        "condition": "NEW",
        "location_id": loc_active.id,
        "part_id": part.id,
        "valid_until": (date.today() + timedelta(days=30)).isoformat(),
    }
    resp2 = client.post("/api/admin/surplus", json=payload_part, headers=headers)
    assert resp2.status_code == status.HTTP_201_CREATED, resp2.text
    data2 = resp2.json()
    assert data2["part"]["part_number"] == "BRG-6205"

    # 3. Validation: Inactive location -> 422 invalid_location
    bad_loc = dict(payload_mach, location_id=loc_inactive.id)
    resp3 = client.post("/api/admin/surplus", json=bad_loc, headers=headers)
    assert resp3.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp3.json()["code"] == "invalid_location"

    # 4. Validation: Non-existent part_id -> 422 invalid_part
    bad_part = dict(payload_part, part_id=999999)
    resp4 = client.post("/api/admin/surplus", json=bad_part, headers=headers)
    assert resp4.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp4.json()["code"] == "invalid_part"

    # 5. Validation: Past valid_until -> 422 invalid_valid_until
    bad_date = dict(payload_part, valid_until=(date.today() - timedelta(days=1)).isoformat())
    resp5 = client.post("/api/admin/surplus", json=bad_date, headers=headers)
    assert resp5.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp5.json()["code"] == "invalid_valid_until"


def test_surplus_list_and_visibility_rules(client, db_session):
    """Employee only sees AVAILABLE and RESERVED items with valid dates at active locations."""
    loc_active = create_location(db_session, code="LOC-A", name="Location A")
    loc_inactive = create_location(db_session, code="LOC-B", name="Location B", is_active=False)
    admin = create_user(db_session, employee_id="ADM_VIS", role=UserRole.STORE_ADMIN, location=loc_active)
    emp = create_user(db_session, employee_id="EMP_VIS", role=UserRole.EMPLOYEE, location=loc_active)

    # 1. Available item (visible)
    it_avail = create_surplus_item_db(db_session, admin, loc_active, title="Available Motor", status=SurplusStatus.AVAILABLE)
    # 2. Reserved item (visible)
    it_res = create_surplus_item_db(db_session, admin, loc_active, title="Reserved Motor", status=SurplusStatus.RESERVED)
    # 3. Claimed item (hidden from employee)
    it_claim = create_surplus_item_db(db_session, admin, loc_active, title="Claimed Motor", status=SurplusStatus.CLAIMED)
    # 4. Withdrawn item (hidden from employee)
    it_with = create_surplus_item_db(db_session, admin, loc_active, title="Withdrawn Motor", status=SurplusStatus.WITHDRAWN)
    # 5. Inactive location item (hidden from employee)
    it_inact = create_surplus_item_db(db_session, admin, loc_inactive, title="Inactive Loc Motor", status=SurplusStatus.AVAILABLE)
    # 6. Expired item (hidden from employee)
    it_exp = create_surplus_item_db(db_session, admin, loc_active, title="Expired Motor", status=SurplusStatus.AVAILABLE, valid_until=date.today() - timedelta(days=2))

    emp_headers = login_as(client, "EMP_VIS")
    admin_headers = login_as(client, "ADM_VIS")

    # Employee list
    resp_emp = client.get("/api/surplus", headers=emp_headers)
    assert resp_emp.status_code == 200
    emp_ids = [it["id"] for it in resp_emp.json()["items"]]
    assert it_avail.id in emp_ids
    assert it_res.id in emp_ids
    assert it_claim.id not in emp_ids
    assert it_with.id not in emp_ids
    assert it_inact.id not in emp_ids
    assert it_exp.id not in emp_ids

    # Employee detail 404 guards
    assert client.get(f"/api/surplus/{it_claim.id}", headers=emp_headers).status_code == 404
    assert client.get(f"/api/surplus/{it_with.id}", headers=emp_headers).status_code == 404
    assert client.get(f"/api/surplus/{it_inact.id}", headers=emp_headers).status_code == 404
    assert client.get(f"/api/surplus/{it_exp.id}", headers=emp_headers).status_code == 404

    # Admin list sees all (including CLAIMED, WITHDRAWN, INACTIVE, EXPIRED)
    resp_adm = client.get("/api/admin/surplus", headers=admin_headers)
    assert resp_adm.status_code == 200
    adm_ids = [it["id"] for it in resp_adm.json()["items"]]
    assert it_avail.id in adm_ids
    assert it_claim.id in adm_ids
    assert it_with.id in adm_ids
    assert it_inact.id in adm_ids
    assert it_exp.id in adm_ids

    # Admin can open detail of claimed/withdrawn item
    assert client.get(f"/api/surplus/{it_claim.id}", headers=admin_headers).status_code == 200


def test_own_location_first_sorting(client, db_session):
    """When sorted by newest, caller's own location listings appear first."""
    loc_bengaluru = create_location(db_session, code="ITC-BLR", name="ITC Bengaluru")
    loc_pune = create_location(db_session, code="ITC-PUN", name="ITC Pune")
    admin = create_user(db_session, employee_id="ADM_LOC", role=UserRole.STORE_ADMIN, location=loc_bengaluru)
    emp_pune = create_user(db_session, employee_id="EMP_PUN", role=UserRole.EMPLOYEE, location=loc_pune)

    # Bengaluru item created earlier
    item_blr = create_surplus_item_db(db_session, admin, loc_bengaluru, title="Bengaluru Gearbox")
    # Pune item created later
    item_pun = create_surplus_item_db(db_session, admin, loc_pune, title="Pune Pneumatic Valve")

    # When Pune employee searches with sort=newest, Pune item must come first
    pune_headers = login_as(client, "EMP_PUN")
    resp = client.get("/api/surplus?sort=newest&order=desc", headers=pune_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 2
    assert items[0]["id"] == item_pun.id
    assert items[0]["is_my_location"] is True
    assert items[1]["id"] == item_blr.id
    assert items[1]["is_my_location"] is False


def test_surplus_filters_and_escaped_search(client, db_session):
    """Filter options endpoint works; multi-term search with SQL wildcard characters is safely escaped."""
    loc = create_location(db_session, code="LOC-FLT", name="Filter Plant")
    admin = create_user(db_session, employee_id="ADM_FLT", role=UserRole.STORE_ADMIN, location=loc)
    part = create_part(db_session, part_number="BRG_6205%SPECIAL", name="Ball Bearing 100% Steel")

    create_surplus_item_db(
        db_session,
        admin,
        loc,
        title="100% Pure Steel_Bar (Surplus)",
        description="High grade 100% steel_rods",
        part=part,
    )

    headers = login_as(client, "ADM_FLT")

    # 1. Filter options endpoint
    resp_flt = client.get("/api/surplus/filters", headers=headers)
    assert resp_flt.status_code == 200
    filters = resp_flt.json()
    assert "MACHINERY" in filters["kinds"]
    assert any(l["id"] == loc.id for l in filters["locations"])

    # 2. Escaped multi-term search
    # Searching for literal % and _
    resp_search = client.get("/api/surplus?q=100%25%20Steel_Bar", headers=headers)
    assert resp_search.status_code == 200
    data = resp_search.json()
    assert data["total"] == 1
    assert "100% Pure Steel_Bar" in data["items"][0]["title"]

    # Searching by linked part number containing _ and %
    resp_part_search = client.get("/api/surplus?q=BRG_6205%25SPECIAL", headers=headers)
    assert resp_part_search.status_code == 200
    assert resp_part_search.json()["total"] == 1


def test_interest_upsert_bounds_and_own_listing(client, db_session):
    """Interest upsert enforces quantity bounds, 409 on own listing, and notification generation."""
    loc_blr = create_location(db_session, code="ITC-BLR", name="ITC Bengaluru")
    loc_pun = create_location(db_session, code="ITC-PUN", name="ITC Pune")
    admin_blr = create_user(db_session, employee_id="ADM_BLR", role=UserRole.STORE_ADMIN, location=loc_blr)
    emp_pun = create_user(db_session, employee_id="EMP_PUN01", role=UserRole.EMPLOYEE, location=loc_pun)

    item = create_surplus_item_db(
        db_session,
        admin_blr,
        loc_blr,
        title="Spare Conveyor Motor",
        quantity=5,
        unit="units",
    )

    admin_headers = login_as(client, "ADM_BLR")
    emp_headers = login_as(client, "EMP_PUN01")

    # 1. Creator cannot express interest in own listing -> 409 own_listing
    resp_own = client.put(f"/api/surplus/{item.id}/interest", json={"quantity_requested": 1}, headers=admin_headers)
    assert resp_own.status_code == status.HTTP_409_CONFLICT
    assert resp_own.json()["code"] == "own_listing"

    # 2. Employee requests quantity > item quantity -> 422 quantity_exceeds_available
    resp_excess = client.put(f"/api/surplus/{item.id}/interest", json={"quantity_requested": 10}, headers=emp_headers)
    assert resp_excess.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp_excess.json()["code"] == "quantity_exceeds_available"

    # 3. Valid interest expression
    resp_ok = client.put(
        f"/api/surplus/{item.id}/interest",
        json={"quantity_requested": 3, "message": "Needed for packaging line"},
        headers=emp_headers,
    )
    assert resp_ok.status_code == 200
    intr_data = resp_ok.json()
    assert intr_data["quantity_requested"] == 3

    # Check notification delivered to admin at item location
    notifs = db_session.scalars(
        select(Notification).where(
            Notification.recipient_user_id == admin_blr.id,
            Notification.surplus_item_id == item.id,
        )
    ).all()
    assert len(notifs) == 1
    assert "is interested in 3 units of Spare Conveyor Motor at ITC Bengaluru" in notifs[0].message

    # 4. Replaying interest updates the row and does NOT generate a duplicate notification within 5 min
    resp_replay = client.put(
        f"/api/surplus/{item.id}/interest",
        json={"quantity_requested": 4, "message": "Updated request for packaging line"},
        headers=emp_headers,
    )
    assert resp_replay.status_code == 200
    assert resp_replay.json()["quantity_requested"] == 4

    notifs_after = db_session.scalars(
        select(Notification).where(
            Notification.recipient_user_id == admin_blr.id,
            Notification.surplus_item_id == item.id,
        )
    ).all()
    assert len(notifs_after) == 1  # No duplicate notification!


def test_withdraw_interest(client, db_session):
    """Interest withdrawal is idempotent and removes the interest record."""
    loc = create_location(db_session, code="LOC-WDR", name="Withdraw Loc")
    admin = create_user(db_session, employee_id="ADM_WDR", role=UserRole.STORE_ADMIN, location=loc)
    emp = create_user(db_session, employee_id="EMP_WDR", role=UserRole.EMPLOYEE, location=loc)

    item = create_surplus_item_db(db_session, admin, loc, title="Pneumatic Actuator", quantity=2)
    emp_headers = login_as(client, "EMP_WDR")

    # Express interest
    client.put(f"/api/surplus/{item.id}/interest", json={"quantity_requested": 1}, headers=emp_headers)

    # Withdraw interest -> 204
    resp_del = client.delete(f"/api/surplus/{item.id}/interest", headers=emp_headers)
    assert resp_del.status_code == status.HTTP_204_NO_CONTENT

    # Verify interest removed
    interests = db_session.scalars(
        select(SurplusInterest).where(
            SurplusInterest.item_id == item.id,
            SurplusInterest.user_id == emp.id,
        )
    ).all()
    assert len(interests) == 0

    # Idempotent second delete -> 204
    resp_del2 = client.delete(f"/api/surplus/{item.id}/interest", headers=emp_headers)
    assert resp_del2.status_code == status.HTTP_204_NO_CONTENT


def test_status_transitions(client, db_session):
    """Lifecycle transitions obey allowed states; CLAIMED is terminal; empty update gives 422."""
    loc = create_location(db_session, code="LOC-TRN", name="Transition Loc")
    admin = create_user(db_session, employee_id="ADM_TRN", role=UserRole.STORE_ADMIN, location=loc)
    item = create_surplus_item_db(db_session, admin, loc, title="Hydraulic Pump", status=SurplusStatus.AVAILABLE)
    admin_headers = login_as(client, "ADM_TRN")

    # AVAILABLE -> RESERVED (Allowed)
    r1 = client.post(f"/api/admin/surplus/{item.id}/status", json={"status": "RESERVED"}, headers=admin_headers)
    assert r1.status_code == 200
    assert r1.json()["status"] == "RESERVED"

    # RESERVED -> CLAIMED (Allowed)
    r2 = client.post(f"/api/admin/surplus/{item.id}/status", json={"status": "CLAIMED"}, headers=admin_headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "CLAIMED"

    # CLAIMED -> AVAILABLE (Forbidden: CLAIMED is terminal -> 409 invalid_transition)
    r3 = client.post(f"/api/admin/surplus/{item.id}/status", json={"status": "AVAILABLE"}, headers=admin_headers)
    assert r3.status_code == status.HTTP_409_CONFLICT
    assert r3.json()["code"] == "invalid_transition"

    # Test WITHDRAWN -> AVAILABLE
    item2 = create_surplus_item_db(db_session, admin, loc, title="Centrifugal Fan", status=SurplusStatus.WITHDRAWN)
    r4 = client.post(f"/api/admin/surplus/{item2.id}/status", json={"status": "AVAILABLE"}, headers=admin_headers)
    assert r4.status_code == 200
    assert r4.json()["status"] == "AVAILABLE"

    # Test PATCH empty body -> 422 empty_update
    r_empty = client.patch(f"/api/admin/surplus/{item.id}", json={}, headers=admin_headers)
    assert r_empty.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert r_empty.json()["code"] == "empty_update"


def test_image_upload_and_delete(client, db_session):
    """Magic bytes verification, server-generated filename, and image removal."""
    loc = create_location(db_session, code="LOC-IMG", name="Image Loc")
    admin = create_user(db_session, employee_id="ADM_IMG", role=UserRole.STORE_ADMIN, location=loc)
    item = create_surplus_item_db(db_session, admin, loc, title="Gear Reducer")
    admin_headers = login_as(client, "ADM_IMG")

    # 1. Invalid magic bytes (e.g. plain text masquerading as image)
    fake_png = b"Not a real PNG content at all"
    r_bad = client.post(
        f"/api/admin/surplus/{item.id}/image",
        files={"file": ("test.png", fake_png, "image/png")},
        headers=admin_headers,
    )
    assert r_bad.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert r_bad.json()["code"] == "invalid_image"

    # 2. Valid PNG magic bytes
    valid_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    r_ok = client.post(
        f"/api/admin/surplus/{item.id}/image",
        files={"file": ("photo.png", valid_png, "image/png")},
        headers=admin_headers,
    )
    assert r_ok.status_code == 200
    data = r_ok.json()
    assert data["image_url"] is not None
    assert "/uploads/" in data["image_url"]

    # 3. Delete image
    r_del = client.delete(f"/api/admin/surplus/{item.id}/image", headers=admin_headers)
    assert r_del.status_code == 200
    assert r_del.json()["image_url"] is None


def test_admin_interests_roster(client, db_session):
    """Admin can view the full roster of users who expressed interest in a listing."""
    loc = create_location(db_session, code="LOC-RST", name="Roster Loc")
    admin = create_user(db_session, employee_id="ADM_RST", role=UserRole.STORE_ADMIN, location=loc)
    emp1 = create_user(db_session, employee_id="EMP_RST1", name="Roster User One", location=loc)
    emp2 = create_user(db_session, employee_id="EMP_RST2", name="Roster User Two", location=loc)

    item = create_surplus_item_db(db_session, admin, loc, title="Forklift Battery", quantity=10)

    # Both employees express interest
    h1 = login_as(client, "EMP_RST1")
    h2 = login_as(client, "EMP_RST2")
    client.put(f"/api/surplus/{item.id}/interest", json={"quantity_requested": 2, "message": "For Bay 1"}, headers=h1)
    client.put(f"/api/surplus/{item.id}/interest", json={"quantity_requested": 4, "message": "For Bay 2"}, headers=h2)

    # Admin checks roster
    admin_headers = login_as(client, "ADM_RST")
    resp = client.get(f"/api/admin/surplus/{item.id}/interests", headers=admin_headers)
    assert resp.status_code == 200
    roster = resp.json()
    assert len(roster) == 2
    emp_ids = {r["user"]["employee_id"] for r in roster}
    assert "EMP_RST1" in emp_ids
    assert "EMP_RST2" in emp_ids


def test_surplus_concurrency_interests(client, db_session):
    """10 simultaneous threads by 10 different employees expressing interest in the same item."""
    loc = create_location(db_session, code="LOC-CNC", name="Concurrency Loc")
    admin = create_user(db_session, employee_id="ADM_CNC", role=UserRole.STORE_ADMIN, location=loc)
    item = create_surplus_item_db(db_session, admin, loc, title="High Capacity Chiller", quantity=100)
    item_id = item.id

    # Create 10 distinct employees and auth tokens
    tokens = []
    for i in range(10):
        emp_id = f"EMP_CNC_{i:02d}"
        create_user(db_session, employee_id=emp_id, name=f"Concurrent Employee {i}", location=loc)
        tokens.append(login_as(client, emp_id))

    def submit_interest(token):
        return client.put(
            f"/api/surplus/{item_id}/interest",
            json={"quantity_requested": 1, "message": "Concurrent demand"},
            headers=token,
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(submit_interest, tokens))

    # All 10 requests must succeed
    for r in results:
        assert r.status_code == 200, f"Thread request failed: {r.status_code} - {r.text}"

    # Verify exactly 10 rows in surplus_interests
    with TestingSessionLocal() as session:
        count = session.scalar(
            select(func.count(SurplusInterest.id)).where(SurplusInterest.item_id == item_id)
        )
        assert count == 10

