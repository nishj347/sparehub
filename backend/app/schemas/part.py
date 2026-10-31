"""Pydantic schemas for SparePart catalog management."""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.storage import storage_service
from app.models.enums import TransactionType
from app.schemas.location import normalize_whitespace


def normalize_part_number(v: str) -> str:
    """Trim and uppercase part number, validating alphanumeric with allowed special characters."""
    cleaned = v.strip().upper()
    if not re.match(r"^[A-Z0-9][A-Z0-9._/-]*$", cleaned):
        raise ValueError(
            "Part number must start with an alphanumeric character and contain only uppercase letters, numbers, hyphens, periods, underscores, and forward slashes."
        )
    return cleaned


class SpecItem(BaseModel):
    """Key-value representation of a single technical specification."""

    key: str = Field(..., min_length=1, max_length=50, description="Specification attribute name")
    value: str = Field(..., min_length=1, max_length=200, description="Specification value")

    @field_validator("key", "value", mode="before")
    @classmethod
    def clean_strings(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            if not cleaned:
                raise ValueError("Specification key and value cannot be empty")
            return cleaned
        return str(v)


class MachineBrief(BaseModel):
    """Minimal representation of a machine linked to a part."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class LocationBrief(BaseModel):
    """Minimal representation of a plant location."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class UserBrief(BaseModel):
    """Minimal representation of an employee/admin user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    employee_id: str


class InitialStockCreate(BaseModel):
    """Initial stock configuration when registering a new part in catalog."""

    location_id: int = Field(..., description="ID of active facility location")
    quantity: int = Field(0, ge=0, description="Opening stock quantity")
    store_name: Optional[str] = Field(None, max_length=60)
    rack: Optional[str] = Field(None, max_length=60)
    bin: Optional[str] = Field(None, max_length=60)
    min_stock_level: int = Field(0, ge=0, description="Low stock alert threshold")

    @field_validator("store_name", "rack", "bin", mode="before")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            return cleaned if cleaned else None
        return v


def validate_specifications_input(v: Any) -> Optional[Dict[str, str]]:
    """Validate specifications from either list of SpecItem/dicts or dictionary.

    Enforces max 20 entries, key <= 50, value <= 200, no empty keys, no duplicate keys.
    Returns normalized dictionary for database storage.
    """
    if v is None:
        return None

    result: Dict[str, str] = {}
    seen_keys = set()

    if isinstance(v, list):
        if len(v) > 20:
            raise ValueError("Specifications cannot exceed 20 entries")
        for item in v:
            if isinstance(item, dict):
                k = normalize_whitespace(str(item.get("key", "")))
                val = normalize_whitespace(str(item.get("value", "")))
            elif hasattr(item, "key") and hasattr(item, "value"):
                k = normalize_whitespace(str(item.key))
                val = normalize_whitespace(str(item.value))
            else:
                raise ValueError("Invalid specification item format")

            if not k:
                raise ValueError("Specification key cannot be empty")
            if len(k) > 50:
                raise ValueError(f"Specification key '{k}' exceeds maximum 50 characters")
            if not val:
                raise ValueError("Specification value cannot be empty")
            if len(val) > 200:
                raise ValueError(f"Specification value for '{k}' exceeds maximum 200 characters")

            k_lower = k.lower()
            if k_lower in seen_keys:
                raise ValueError(f"Duplicate specification key: '{k}'")
            seen_keys.add(k_lower)
            result[k] = val

    elif isinstance(v, dict):
        if len(v) > 20:
            raise ValueError("Specifications cannot exceed 20 entries")
        for k_raw, val_raw in v.items():
            k = normalize_whitespace(str(k_raw))
            val = normalize_whitespace(str(val_raw))
            if not k:
                raise ValueError("Specification key cannot be empty")
            if len(k) > 50:
                raise ValueError(f"Specification key '{k}' exceeds maximum 50 characters")
            if not val:
                raise ValueError("Specification value cannot be empty")
            if len(val) > 200:
                raise ValueError(f"Specification value for '{k}' exceeds maximum 200 characters")

            k_lower = k.lower()
            if k_lower in seen_keys:
                raise ValueError(f"Duplicate specification key: '{k}'")
            seen_keys.add(k_lower)
            result[k] = val
    else:
        raise ValueError("Specifications must be a list of key-value items or a dictionary")

    return result


class PartCreate(BaseModel):
    """Payload for creating a new catalog spare part."""

    part_number: str = Field(..., min_length=1, max_length=40, description="Unique manufacturer/catalog part number")
    name: str = Field(..., min_length=1, max_length=150, description="Part display name")
    category: str = Field(..., min_length=1, max_length=60, description="Component category")
    manufacturer: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    specifications: Optional[Union[List[SpecItem], Dict[str, Any]]] = None
    machine_ids: Optional[List[int]] = Field(None, description="Optional machine IDs to link")
    initial_stock: Optional[InitialStockCreate] = Field(None, description="Optional initial stock opening")

    @field_validator("part_number", mode="before")
    @classmethod
    def clean_part_number(cls, v: str) -> str:
        if isinstance(v, str):
            return normalize_part_number(v)
        return v

    @field_validator("name", "category", mode="before")
    @classmethod
    def clean_required_strings(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            if not cleaned:
                raise ValueError("Field cannot be empty")
            return cleaned
        return v

    @field_validator("manufacturer", "description", mode="before")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            return cleaned if cleaned else None
        return v

    @field_validator("specifications")
    @classmethod
    def clean_specs(cls, v: Any) -> Optional[Dict[str, str]]:
        return validate_specifications_input(v)


class PartUpdate(BaseModel):
    """Payload for updating an existing catalog spare part (part_number is immutable)."""

    name: Optional[str] = Field(None, min_length=1, max_length=150)
    category: Optional[str] = Field(None, min_length=1, max_length=60)
    manufacturer: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    specifications: Optional[Union[List[SpecItem], Dict[str, Any]]] = None
    machine_ids: Optional[List[int]] = None

    @field_validator("name", "category", mode="before")
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            if not cleaned:
                raise ValueError("Field cannot be empty")
            return cleaned
        return v

    @field_validator("manufacturer", "description", mode="before")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = normalize_whitespace(v)
            return cleaned if cleaned else None
        return v

    @field_validator("specifications")
    @classmethod
    def clean_specs(cls, v: Any) -> Optional[Dict[str, str]]:
        return validate_specifications_input(v)


class PartListItem(BaseModel):
    """Part representation in paginated catalog lists."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    part_number: str
    name: str
    category: str
    manufacturer: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool
    total_quantity: int
    location_count: int
    low_stock: bool
    out_of_stock: bool
    machines: List[MachineBrief] = Field(default_factory=list)
    updated_at: datetime


class InventoryItemDetail(BaseModel):
    """Inventory row with detailed location info and stock flags."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    location: LocationBrief
    quantity: int
    store_name: Optional[str] = None
    rack: Optional[str] = None
    bin: Optional[str] = None
    min_stock_level: int
    low_stock: bool
    out_of_stock: bool
    updated_at: datetime


class TransactionBrief(BaseModel):
    """Recent inventory transaction audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    type: TransactionType
    quantity_change: int
    quantity_after: int
    user: Optional[UserBrief] = None
    location: LocationBrief
    notes: Optional[str] = None


class PartDetail(BaseModel):
    """Detailed spare part view including inventory breakdown and recent activity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    part_number: str
    name: str
    category: str
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    specifications: List[SpecItem] = Field(default_factory=list)
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_quantity: int
    location_count: int
    low_stock: bool
    out_of_stock: bool
    machines: List[MachineBrief] = Field(default_factory=list)
    inventory: List[InventoryItemDetail] = Field(default_factory=list)
    recent_transactions: List[TransactionBrief] = Field(default_factory=list)

    @field_validator("specifications", mode="before")
    @classmethod
    def transform_specs(cls, v: Any) -> List[SpecItem]:
        if isinstance(v, dict):
            return [SpecItem(key=k, value=str(val)) for k, val in v.items()]
        if isinstance(v, list):
            items = []
            for item in v:
                if isinstance(item, dict):
                    items.append(SpecItem(key=item.get("key", ""), value=str(item.get("value", ""))))
                elif isinstance(item, SpecItem):
                    items.append(item)
            return items
        return []

