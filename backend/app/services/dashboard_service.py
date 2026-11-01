"""Service layer for the Admin Dashboard (Module 10A)."""
from datetime import datetime, timezone
import zoneinfo
from typing import List

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.storage import storage_service
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.spare_part import SparePart
from app.schemas.dashboard import (
    DashboardActivityItem,
    DashboardActor,
    DashboardLocationBrief,
    DashboardLowStockItem,
    DashboardLowStockPart,
    DashboardPartBrief,
    DashboardResponse,
    DashboardStats,
)


def get_admin_dashboard(db: Session) -> DashboardResponse:
    """Retrieve all operational metrics, low stock items, and recent activity for the admin dashboard.

    Executes in exactly 4 constant queries:
    1. Composite scalar stats query (total_parts, total_units, low_stock_parts, out_of_stock_parts, todays_issues, todays_units_issued)
    2. Low stock total count query
    3. Low stock items (up to 10 worst rows with joined parts and locations)
    4. Recent activity (last 10 ledger rows with joined parts, locations, and users)
    """
    settings = get_settings()
    tz = zoneinfo.ZoneInfo(settings.APP_TIMEZONE)
    now_tz = datetime.now(tz)
    start_of_today_tz = datetime(now_tz.year, now_tz.month, now_tz.day, 0, 0, 0, tzinfo=tz)
    start_of_today_utc = start_of_today_tz.astimezone(timezone.utc)

    # 1. Composite query for key performance indicator metrics
    stats_sql = text("""
        SELECT
            (
                SELECT count(*)
                FROM spare_parts
                WHERE is_active = true
            ) AS total_parts,
            (
                SELECT coalesce(sum(i.quantity), 0)
                FROM inventory i
                JOIN spare_parts sp ON i.part_id = sp.id
                JOIN locations l ON i.location_id = l.id
                WHERE sp.is_active = true AND l.is_active = true
            ) AS total_units,
            (
                SELECT count(DISTINCT i.part_id)
                FROM inventory i
                JOIN spare_parts sp ON i.part_id = sp.id
                JOIN locations l ON i.location_id = l.id
                WHERE sp.is_active = true
                  AND l.is_active = true
                  AND i.min_stock_level > 0
                  AND i.quantity > 0
                  AND i.quantity <= i.min_stock_level
            ) AS low_stock_parts,
            (
                SELECT count(*)
                FROM spare_parts sp
                WHERE sp.is_active = true
                  AND coalesce((
                      SELECT sum(i.quantity)
                      FROM inventory i
                      JOIN locations l ON i.location_id = l.id
                      WHERE i.part_id = sp.id AND l.is_active = true
                  ), 0) = 0
            ) AS out_of_stock_parts,
            (
                SELECT count(*)
                FROM inventory_transactions
                WHERE transaction_type = 'ISSUED'
                  AND created_at >= :start_utc
            ) AS todays_issues,
            (
                SELECT coalesce(sum(abs(quantity_change)), 0)
                FROM inventory_transactions
                WHERE transaction_type = 'ISSUED'
                  AND created_at >= :start_utc
            ) AS todays_units_issued
    """)
    stats_row = db.execute(stats_sql, {"start_utc": start_of_today_utc}).mappings().first()
    stats = DashboardStats(
        total_parts=stats_row["total_parts"] if stats_row else 0,
        total_units=stats_row["total_units"] if stats_row else 0,
        low_stock_parts=stats_row["low_stock_parts"] if stats_row else 0,
        out_of_stock_parts=stats_row["out_of_stock_parts"] if stats_row else 0,
        todays_issues=stats_row["todays_issues"] if stats_row else 0,
        todays_units_issued=stats_row["todays_units_issued"] if stats_row else 0,
    )

    # 2. Total count of low-stock inventory rows matching the business rule
    low_stock_total_stmt = (
        select(func.count(Inventory.id))
        .join(SparePart, Inventory.part_id == SparePart.id)
        .join(Location, Inventory.location_id == Location.id)
        .where(
            SparePart.is_active.is_(True),
            Location.is_active.is_(True),
            Inventory.min_stock_level > 0,
            Inventory.quantity <= Inventory.min_stock_level,
        )
    )
    low_stock_total = db.scalar(low_stock_total_stmt) or 0

    # 3. Top 10 worst low-stock inventory items
    low_stock_items_stmt = (
        select(Inventory)
        .join(SparePart, Inventory.part_id == SparePart.id)
        .join(Location, Inventory.location_id == Location.id)
        .options(
            joinedload(Inventory.part),
            joinedload(Inventory.location),
        )
        .where(
            SparePart.is_active.is_(True),
            Location.is_active.is_(True),
            Inventory.min_stock_level > 0,
            Inventory.quantity <= Inventory.min_stock_level,
        )
        .order_by(
            (Inventory.quantity - Inventory.min_stock_level).asc(),
            SparePart.name.asc(),
            Inventory.id.asc(),
        )
        .limit(10)
    )
    low_stock_records = db.scalars(low_stock_items_stmt).all()
    low_stock_items: List[DashboardLowStockItem] = []
    for inv in low_stock_records:
        shortfall = max(0, inv.min_stock_level - inv.quantity)
        img_url = storage_service.public_url(inv.part.image_path) if inv.part.image_path else None
        low_stock_items.append(
            DashboardLowStockItem(
                inventory_id=inv.id,
                part=DashboardLowStockPart(
                    id=inv.part.id,
                    part_number=inv.part.part_number,
                    name=inv.part.name,
                    image_url=img_url,
                ),
                location=DashboardLocationBrief(
                    id=inv.location.id,
                    name=inv.location.name,
                    code=inv.location.code,
                ),
                quantity=inv.quantity,
                min_stock_level=inv.min_stock_level,
                shortfall=shortfall,
            )
        )

    # 4. Recent activity: last 10 ledger transactions
    recent_activity_stmt = (
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.part),
            joinedload(InventoryTransaction.location),
            joinedload(InventoryTransaction.user),
        )
        .order_by(InventoryTransaction.created_at.desc(), InventoryTransaction.id.desc())
        .limit(10)
    )
    recent_records = db.scalars(recent_activity_stmt).all()
    recent_activity: List[DashboardActivityItem] = []
    for tx in recent_records:
        tx_type = tx.transaction_type.value if hasattr(tx.transaction_type, "value") else str(tx.transaction_type)
        actor = (
            DashboardActor(employee_id=tx.user.employee_id, name=tx.user.name)
            if tx.user
            else None
        )
        recent_activity.append(
            DashboardActivityItem(
                id=tx.id,
                created_at=tx.created_at,
                type=tx_type,
                quantity_change=tx.quantity_change,
                part=DashboardPartBrief(
                    id=tx.part.id,
                    part_number=tx.part.part_number,
                    name=tx.part.name,
                ),
                location=DashboardLocationBrief(
                    id=tx.location.id,
                    name=tx.location.name,
                    code=tx.location.code,
                ),
                actor=actor,
            )
        )

    return DashboardResponse(
        stats=stats,
        recent_activity=recent_activity,
        low_stock_items=low_stock_items,
        low_stock_total=low_stock_total,
        generated_at=datetime.now(timezone.utc),
    )

