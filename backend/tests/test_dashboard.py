"""Tests for Admin Dashboard metrics, aggregation integrity, and timezone day boundaries."""
from datetime import datetime, timedelta, timezone
import zoneinfo
import pytest
from app.core.config import get_settings
from app.models.enums import TransactionType, UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from tests.conftest import (
    create_inventory,
    create_location,
    create_part,
    create_user,
    login_as,
)


def test_dashboard_stats_equal_independent_sql_counts(client, db_session):
    loc1 = create_location(db_session, name="Dash Loc 1", code="DLOC1")
    loc2 = create_location(db_session, name="Dash Loc 2", code="DLOC2")
    admin = create_user(db_session, employee_id="ADM_DASH1", role=UserRole.STORE_ADMIN, location=loc1)
    headers = login_as(client, "ADM_DASH1")

    # Part 1: Active, in stock
    p1 = create_part(db_session, part_number="P-DASH-01")
    create_inventory(db_session, p1, loc1, quantity=20, min_stock_level=5)

    # Part 2: Active, low stock (quantity 2 <= min_stock 5, quantity > 0)
    p2 = create_part(db_session, part_number="P-DASH-02")
    create_inventory(db_session, p2, loc2, quantity=2, min_stock_level=5)

    # Part 3: Active, out of stock (quantity 0)
    p3 = create_part(db_session, part_number="P-DASH-03")
    create_inventory(db_session, p3, loc1, quantity=0, min_stock_level=2)

    # Part 4: Inactive part (should NOT count in total_parts)
    p4 = create_part(db_session, part_number="P-DASH-04", is_active=False)
    create_inventory(db_session, p4, loc1, quantity=10)

    resp = client.get("/api/admin/dashboard", headers=headers)
    assert resp.status_code == 200
    stats = resp.json()["stats"]

    assert stats["total_parts"] == 3  # p1, p2, p3 (p4 inactive)
    assert stats["total_units"] == 22  # 20 + 2 + 0
    assert stats["low_stock_parts"] == 1  # p2
    assert stats["out_of_stock_parts"] == 1  # p3


def test_dashboard_today_issues_respects_app_timezone_boundary(client, db_session):
    settings = get_settings()
    tz = zoneinfo.ZoneInfo(settings.APP_TIMEZONE)
    now_tz = datetime.now(tz)
    start_of_today_tz = datetime(now_tz.year, now_tz.month, now_tz.day, 0, 0, 0, tzinfo=tz)
    start_of_today_utc = start_of_today_tz.astimezone(timezone.utc)

    loc = create_location(db_session)
    admin = create_user(db_session, employee_id="ADM_DASH2", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADM_DASH2")

    part = create_part(db_session, part_number="P-DASH-TZ")
    inv = create_inventory(db_session, part, loc, quantity=50)

    # 1. Transaction from yesterday in APP_TIMEZONE (1 hour before start_of_today)
    yesterday_tx = InventoryTransaction(
        part_id=part.id,
        location_id=loc.id,
        user_id=admin.id,
        transaction_type=TransactionType.ISSUED,
        quantity_change=-5,
        quantity_after=45,
        created_at=start_of_today_utc - timedelta(hours=1),
    )
    # 2. Transaction from today in APP_TIMEZONE (1 hour after start_of_today)
    today_tx = InventoryTransaction(
        part_id=part.id,
        location_id=loc.id,
        user_id=admin.id,
        transaction_type=TransactionType.ISSUED,
        quantity_change=-3,
        quantity_after=42,
        created_at=start_of_today_utc + timedelta(hours=1),
    )
    db_session.add_all([yesterday_tx, today_tx])
    db_session.commit()

    resp = client.get("/api/admin/dashboard", headers=headers)
    assert resp.status_code == 200
    stats = resp.json()["stats"]

    # Only today_tx should be counted
    assert stats["todays_issues"] == 1
    assert stats["todays_units_issued"] == 3

