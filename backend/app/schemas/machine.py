"""Pydantic schemas for Machine master data."""
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.location import normalize_code, normalize_whitespace


class LocationBrief(BaseModel):
    """Brief representation of an assigned location."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class MachineOption(BaseModel):
    """Minimal machine descriptor for dropdown selection lists."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class MachineCreate(BaseModel):
    """Payload for creating a new industrial Machine."""

    name: str = Field(..., min_length=1, max_length=150, description="Machine display name")
    code: str = Field(..., min_length=1, max_length=50, description="Unique machine plant code (e.g. C-14)")
    location_id: Optional[int] = Field(None, description="Optional ID of active facility location")

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v: str) -> str:
        if isinstance(v, str):
            return normalize_whitespace(v)
        return v

    @field_validator("code", mode="before")
    @classmethod
    def clean_code(cls, v: str) -> str:
        if isinstance(v, str):
            return normalize_code(v)
        return v


class MachineUpdate(BaseModel):
    """Payload for updating an existing Machine."""

    name: Optional[str] = Field(None, min_length=1, max_length=150)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    location_id: Optional[int] = Field(None, description="Assign to location or set null to unassign")

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            if not cleaned:
                raise ValueError("Name cannot be empty")
            return cleaned
        return v

    @field_validator("code", mode="before")
    @classmethod
    def clean_code(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return normalize_code(v)
        return v


class MachineRead(BaseModel):
    """Detailed Machine response including linked location and part counts."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    is_active: bool
    created_at: datetime
    location: Optional[LocationBrief] = None
    part_count: int = Field(0, description="Number of linked spare parts in catalog")

