"""Pydantic schemas for Employee Issue History and Admin Activity Ledger (Module 9A)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Employee Issue History Schemas (GET /api/issues/mine) ────────────────────

class MyIssuePartBrief(BaseModel):
    id: int
    part_number: str
    name: str
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MyIssueLocationBrief(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class MyIssueItem(BaseModel):
    transaction_id: int
    created_at: datetime
    part: MyIssuePartBrief
    quantity: int = Field(..., description="Positive number of units issued")
    location: MyIssueLocationBrief
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IssueSummary(BaseModel):
    total_issues: int = Field(0, description="Total matching transaction count")
    total_units: int = Field(0, description="Total units issued across matching transactions")


class MyIssuesResponse(BaseModel):
    items: List[MyIssueItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: IssueSummary


# ── Admin Activity Ledger Schemas (GET /api/admin/activity) ──────────────────

class ActivityActor(BaseModel):
    user_id: int
    employee_id: str
    name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class AdminActivityPartBrief(BaseModel):
    id: int
    part_number: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class AdminActivityLocationBrief(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class AdminActivityItem(BaseModel):
    id: int
    created_at: datetime
    type: str  # ISSUED | RECEIVED | ADJUSTED
    quantity_change: int  # Signed delta (negative for ISSUED)
    quantity_after: int
    part: AdminActivityPartBrief
    location: AdminActivityLocationBrief
    actor: Optional[ActivityActor] = None  # None = "System"
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminActivitySummary(BaseModel):
    total_rows: int = Field(0, description="Total matching transactions")
    units_issued: int = Field(0, description="Sum of positive units issued")
    units_received: int = Field(0, description="Sum of units received")


class AdminActivityResponse(BaseModel):
    items: List[AdminActivityItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: AdminActivitySummary

