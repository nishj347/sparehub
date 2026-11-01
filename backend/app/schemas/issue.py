"""Pydantic schemas for the issue-part workflow (POST /api/issues)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IssueRequest(BaseModel):
    """Payload an employee sends to issue (take) a spare part."""

    inventory_id: Optional[int] = Field(None, description="ID of the inventory row to deduct from")
    part_id: Optional[int] = Field(None, description="Optional Part ID if inventory_id is not known")
    location_id: Optional[int] = Field(None, description="Optional Location ID if inventory_id is not known")
    quantity: int = Field(..., ge=1, le=100_000, description="Number of units to take")
    idempotency_key: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[a-zA-Z0-9\-_]+$",
        description="Client-generated unique key to make the request safe to retry",
    )
    notes: Optional[str] = Field(None, max_length=500, description="Optional reason / job reference")


# ── Response nested objects ──────────────────────────────────────────────────

class IssueEmployeeBrief(BaseModel):
    employee_id: str
    name: str

    model_config = {"from_attributes": True}


class IssuePartBrief(BaseModel):
    id: int
    part_number: str
    name: str

    model_config = {"from_attributes": True}


class IssueLocationBrief(BaseModel):
    id: int
    name: str
    code: str

    model_config = {"from_attributes": True}


# ── Top-level response ───────────────────────────────────────────────────────

class IssueResponse(BaseModel):
    transaction_id: int
    issued_at: datetime
    employee: IssueEmployeeBrief
    part: IssuePartBrief
    location: IssueLocationBrief
    store_name: Optional[str]
    rack: Optional[str]
    bin: Optional[str]
    quantity_issued: int
    quantity_remaining: int
    message: str
    idempotent_replay: bool

