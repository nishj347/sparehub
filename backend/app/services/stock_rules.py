"""Shared business rules and SQL expressions for stock level evaluation.

Used across catalog management, inventory tracking, issuance, and notifications.
"""
from typing import Any, Iterable
from sqlalchemy import and_, func, select
from sqlalchemy.sql.elements import BinaryExpression

from app.models.inventory import Inventory
from app.models.spare_part import SparePart


# ==============================================================================
# Plain Python Helpers
# ==============================================================================

def is_out_of_stock(quantity: int) -> bool:
    """True if quantity is zero."""
    return quantity == 0


def is_low_stock(quantity: int, min_stock_level: int) -> bool:
    """True if min_stock_level > 0 and current quantity is at or below threshold."""
    return min_stock_level > 0 and quantity <= min_stock_level


def is_part_low_stock(inventory_items: Iterable[Any]) -> bool:
    """True if ANY assigned inventory location for the part is currently low in stock."""
    return any(is_low_stock(i.quantity, i.min_stock_level) for i in inventory_items)


def is_part_out_of_stock(total_quantity: int) -> bool:
    """True if overall stock of the part across all locations is zero."""
    return total_quantity == 0


# ==============================================================================
# SQL Expressions for Inventory Row Queries
# ==============================================================================

def inventory_out_of_stock_sql() -> BinaryExpression:
    """SQL expression for an inventory row being out of stock (quantity == 0)."""
    return Inventory.quantity == 0


def inventory_low_stock_sql():
    """SQL expression for an inventory row being low on stock."""
    return and_(Inventory.min_stock_level > 0, Inventory.quantity <= Inventory.min_stock_level)


# ==============================================================================
# Correlated Scalar Subqueries for Part Catalog Queries
# ==============================================================================

def part_total_quantity_subquery(part_id_col=SparePart.id):
    """Correlated scalar subquery summing quantity across all locations for a part."""
    return (
        select(func.coalesce(func.sum(Inventory.quantity), 0))
        .where(Inventory.part_id == part_id_col)
        .scalar_subquery()
    )


def part_location_count_subquery(part_id_col=SparePart.id):
    """Correlated scalar subquery counting assigned location records for a part."""
    return (
        select(func.count(Inventory.id))
        .where(Inventory.part_id == part_id_col)
        .scalar_subquery()
    )


def part_low_stock_subquery(part_id_col=SparePart.id):
    """Correlated scalar subquery returning True if any location has low stock."""
    return (
        select(
            func.coalesce(
                func.bool_or(
                    and_(
                        Inventory.min_stock_level > 0,
                        Inventory.quantity <= Inventory.min_stock_level,
                    )
                ),
                False,
            )
        )
        .where(Inventory.part_id == part_id_col)
        .scalar_subquery()
    )


def part_out_of_stock_subquery(part_id_col=SparePart.id):
    """Correlated scalar subquery returning True if total quantity across all locations is 0."""
    return (
        select(func.coalesce(func.sum(Inventory.quantity), 0) == 0)
        .where(Inventory.part_id == part_id_col)
        .scalar_subquery()
    )

