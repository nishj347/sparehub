"""Pydantic schemas for Location master data."""
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_whitespace(v: str) -> str:
    """Trim leading/trailing whitespace and collapse internal space sequences."""
    return re.sub(r"\s+", " ", v.strip())


def normalize_code(v: str) -> str:
    """Trim and uppercase alphanumeric identifier code."""
    cleaned = v.strip().upper()
    if not re.match(r"^[A-Z0-9][A-Z0-9_-]*$", cleaned):
        raise ValueError(
            "Code must start with an alphanumeric character and contain only uppercase letters, numbers, hyphens, and underscores."
        )
    return cleaned


class LocationOption(BaseModel):
    """Minimal location descriptor for dropdown selection lists."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class LocationCreate(BaseModel):
    """Payload for creating a new Location."""

    name: str = Field(..., min_length=1, max_length=100, description="Plant or site name")
    code: str = Field(..., min_length=1, max_length=20, description="Unique uppercase location code")
    city: str = Field(..., min_length=1, max_length=100, description="City where facility is located")

    @field_validator("name", "city", mode="before")
    @classmethod
    def clean_strings(cls, v: str) -> str:
        if isinstance(v, str):
            return normalize_whitespace(v)
        return v

    @field_validator("code", mode="before")
    @classmethod
    def clean_code(cls, v: str) -> str:
        if isinstance(v, str):
            return normalize_code(v)
        return v


class LocationUpdate(BaseModel):
    """Payload for updating an existing Location."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    city: Optional[str] = Field(None, min_length=1, max_length=100)

    @field_validator("name", "city", mode="before")
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            if not cleaned:
                raise ValueError("String cannot be empty")
            return cleaned
        return v

    @field_validator("code", mode="before")
    @classmethod
    def clean_code(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return normalize_code(v)
        return v


class LocationRead(BaseModel):
    """Detailed Location response including aggregate metric counters."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    city: str
    is_active: bool
    created_at: datetime
    user_count: int = Field(0, description="Number of users assigned to this location")
    machine_count: int = Field(0, description="Number of machines assigned to this location")
    stocked_part_count: int = Field(0, description="Number of inventory rows with quantity > 0")

