"""Pydantic schemas for employee-facing part detail view (Module 7A)."""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PublicLocationBrief(BaseModel):
    """Brief representation of an active plant location."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    city: str


class PublicMachineDetail(BaseModel):
    """Machine detail visible to employees."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    location_name: Optional[str] = None


class SpecItem(BaseModel):
    """Key-value representation of a single technical specification."""

    key: str
    value: str


class LocationStockDetail(BaseModel):
    """Per-location stock availability row."""

    model_config = ConfigDict(from_attributes=True)

    inventory_id: Optional[int] = None
    location: PublicLocationBrief
    quantity: int
    store_name: Optional[str] = None
    rack: Optional[str] = None
    bin: Optional[str] = None
    availability_status: str  # IN_STOCK | LOW_STOCK | OUT_OF_STOCK
    is_my_location: bool = False


class EmployeePartDetail(BaseModel):
    """Complete employee-facing spare part detail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    part_number: str
    name: str
    category: str
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    specifications: List[SpecItem] = []
    machines: List[PublicMachineDetail] = []
    total_quantity: int
    availability_status: str  # IN_STOCK | LOW_STOCK | OUT_OF_STOCK
    locations: List[LocationStockDetail] = []

