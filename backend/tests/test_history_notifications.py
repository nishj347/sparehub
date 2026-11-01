"""Tests for issue history and admin in-app notifications isolation and workflows."""
import pytest
from app.models.enums import UserRole
from app.models.notification import Notification
from tests.conftest import (
    create_inventory,
    create_location,
    create_part,
    create_user,
    login_as,
)


def test_issues_mine_shows_only_callers_transactions(client, db_session):
    loc = create_location(db_session)
    user_a = create_user(db_session, employee_id="EMP_HIST_A", email="a@example.com", location=loc)
    user_b = create_user(db_session, employee_id="EMP_HIST_B", email="b@example.com", location=loc)

    headers_a = login_as(client, "EMP_HIST_A")
    headers_b = login_as(client, "EMP_HIST_B")

    part1 = create_part(db_session, part_number="P-HIST-01", name="Part One")
    part2 = create_part(db_session, part_number="P-HIST-02", name="Part Two")

    inv1 = create_inventory(db_session, part1, loc, quantity=10)
    inv2 = create_inventory(db_session, part2, loc, quantity=10)

    # User A issues from inv1
    client.post("/api/issues", json={"inventory_id": inv1.id, "quantity": 1, "idempotency_key": "hist-a-1"}, headers=headers_a)
    # User B issues from inv2
    client.post("/api/issues", json={"inventory_id": inv2.id, "quantity": 2, "idempotency_key": "hist-b-1"}, headers=headers_b)

    # Check /api/issues/mine for User A
    resp_a = client.get("/api/issues/mine", headers=headers_a)
    assert resp_a.status_code == 200
    items_a = resp_a.json()["items"]
    assert len(items_a) == 1
    assert items_a[0]["part"]["part_number"] == "P-HIST-01"

    # Check /api/issues/mine for User B
    resp_b = client.get("/api/issues/mine", headers=headers_b)
    assert resp_b.status_code == 200
    items_b = resp_b.json()["items"]
    assert len(items_b) == 1
    assert items_b[0]["part"]["part_number"] == "P-HIST-02"


def test_admin_notification_isolation_and_unread_lifecycle(client, db_session):
    loc = create_location(db_session)
    admin_a = create_user(db_session, employee_id="ADM_NOTIF_A", role=UserRole.STORE_ADMIN, location=loc)
    admin_b = create_user(db_session, employee_id="ADM_NOTIF_B", role=UserRole.STORE_ADMIN, location=loc)

    headers_a = login_as(client, "ADM_NOTIF_A")
    headers_b = login_as(client, "ADM_NOTIF_B")

    part = create_part(db_session, part_number="P-NOTIF-TEST")

    # Manually seed notifications for admin_a and admin_b
    notif_a1 = Notification(
        recipient_user_id=admin_a.id,
        message="3 units issued",
        is_read=False,
    )
    notif_a2 = Notification(
        recipient_user_id=admin_a.id,
        message="1 unit issued",
        is_read=False,
    )
    notif_b = Notification(
        recipient_user_id=admin_b.id,
        message="5 units issued",
        is_read=False,
    )
    db_session.add_all([notif_a1, notif_a2, notif_b])
    db_session.commit()

    # 1. Unread count for admin A
    resp_count_a = client.get("/api/admin/notifications/unread-count", headers=headers_a)
    assert resp_count_a.status_code == 200
    assert resp_count_a.json()["unread"] == 2

    # 2. Admin B cannot read/mark Admin A's notification (must return 404)
    resp_cross_read = client.post(f"/api/admin/notifications/{notif_a1.id}/read", headers=headers_b)
    assert resp_cross_read.status_code == 404

    # 3. Admin A marks single notification as read
    resp_mark = client.post(f"/api/admin/notifications/{notif_a1.id}/read", headers=headers_a)
    assert resp_mark.status_code == 200
    assert resp_mark.json()["is_read"] is True

    # Unread count now 1
    resp_count_a2 = client.get("/api/admin/notifications/unread-count", headers=headers_a)
    assert resp_count_a2.json()["unread"] == 1

    # 4. Admin A calls read-all
    resp_read_all = client.post("/api/admin/notifications/read-all", headers=headers_a)
    assert resp_read_all.status_code == 200
    assert resp_read_all.json()["updated"] == 1

    # Unread count now 0 for Admin A
    resp_count_a3 = client.get("/api/admin/notifications/unread-count", headers=headers_a)
    assert resp_count_a3.json()["unread"] == 0

    # Admin B's notification is still unread!
    resp_count_b = client.get("/api/admin/notifications/unread-count", headers=headers_b)
    assert resp_count_b.json()["unread"] == 1
