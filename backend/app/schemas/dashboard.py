"""Pydantic schemas for the Admin Dashboard endpoint (Module 10A)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DashboardStats(BaseModel):
    """Core key performance indicator statistics."""

    total_parts: int = Field(..., description="Count of active spare parts")
    total_units: int = Field(..., description="Sum of units across active parts at active locations")
    low_stock_parts: int = Field(..., description="Distinct active parts with at least one low (not out) inventory row at an active location")
    out_of_stock_parts: int = Field(..., description="Active parts with total quantity 0 across active locations")
    todays_issues: int = Field(..., description="Count of ISSUED transactions created today in APP_TIMEZONE")
    todays_units_issued: int = Field(..., description="Total positive units issued today in APP_TIMEZONE")


class DashboardPartBrief(BaseModel):
    id: int
    part_number: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class DashboardLocationBrief(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class DashboardActor(BaseModel):
    employee_id: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class DashboardActivityItem(BaseModel):
    id: int
    created_at: datetime
    type: str  # ISSUED, RECEIVED, ADJUSTED
    quantity_change: int  # Signed delta
    part: DashboardPartBrief
    location: DashboardLocationBrief
    actor: Optional[DashboardActor] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardLowStockPart(BaseModel):
    id: int
    part_number: str
    name: str
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardLowStockItem(BaseModel):
    inventory_id: int
    part: DashboardLowStockPart
    location: DashboardLocationBrief
    quantity: int
    min_stock_level: int
    shortfall: int  # min_stock_level - quantity (>= 0)

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_activity: List[DashboardActivityItem]
    low_stock_items: List[DashboardLowStockItem]
    low_stock_total: int
    generated_at: datetime

