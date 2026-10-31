"""Pydantic schemas for Inventory operations and stock ledger transactions."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.location import normalize_whitespace
from app.schemas.part import LocationBrief


class InventoryAddLocation(BaseModel):
    """Payload for linking a spare part to a new plant facility location."""

    location_id: int = Field(..., description="ID of active facility location")
    quantity: int = Field(0, ge=0, description="Opening stock quantity at this location")
    store_name: Optional[str] = Field(None, max_length=60, description="Store or room name")
    rack: Optional[str] = Field(None, max_length=60, description="Rack identifier")
    bin: Optional[str] = Field(None, max_length=60, description="Bin/shelf identifier")
    min_stock_level: int = Field(0, ge=0, description="Low stock threshold alert")

    @field_validator("store_name", "rack", "bin", mode="before")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            return cleaned if cleaned else None
        return v


class InventoryUpdate(BaseModel):
    """Payload for updating physical storage coordinates and reorder threshold (quantity immutable here)."""

    store_name: Optional[str] = Field(None, max_length=60)
    rack: Optional[str] = Field(None, max_length=60)
    bin: Optional[str] = Field(None, max_length=60)
    min_stock_level: Optional[int] = Field(None, ge=0)

    @field_validator("store_name", "rack", "bin", mode="before")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            return cleaned if cleaned else None
        return v


class StockReceive(BaseModel):
    """Payload for receiving incoming spare parts stock."""

    quantity: int = Field(..., gt=0, description="Quantity received (must be strictly greater than 0)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional receiving notes / invoice reference")

    @field_validator("notes", mode="before")
    @classmethod
    def clean_notes(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            return cleaned if cleaned else None
        return v


class StockAdjust(BaseModel):
    """Payload for inventory cycle count adjustments (reconciliation)."""

    new_quantity: int = Field(..., ge=0, description="Counted physical quantity on hand (>= 0)")
    notes: str = Field(..., min_length=1, max_length=500, description="Mandatory audit justification")

    @field_validator("notes", mode="before")
    @classmethod
    def clean_notes(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            if not cleaned:
                raise ValueError("Notes cannot be empty")
            return cleaned
        return v


class InventoryRead(BaseModel):
    """Detailed response for an inventory record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    location_id: int
    location: LocationBrief
    quantity: int
    store_name: Optional[str] = None
    rack: Optional[str] = None
    bin: Optional[str] = None
    min_stock_level: int
    low_stock: bool
    out_of_stock: bool
    updated_at: datetime

