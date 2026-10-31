# backend/app/schemas/part_public.py
"""Public schema for employee spare‑part discovery (Module 6A)."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# Re‑use existing brief schemas from admin side – they expose only safe fields
# Local brief schemas for employee view (do not import admin schemas)

class PublicLocationBrief(BaseModel):
    """Brief location representation for public API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class PublicMachineBrief(BaseModel):
    """Brief machine representation for public API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class PrimaryLocation(BaseModel):
    """Inventory row chosen as the primary location for a part."""

    location: PublicLocationBrief
    quantity: int
    store_name: Optional[str] = None
    rack: Optional[str] = None
    bin: Optional[str] = None
    is_my_location: bool = False

    model_config = ConfigDict(from_attributes=True)


class PartCard(BaseModel):
    """Employee‑visible part card (search result)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    part_number: str
    name: str
    category: str
    manufacturer: Optional[str] = None
    short_description: Optional[str] = None
    image_url: Optional[str] = None

    # Machines linked to the part – only active machines, max 5
    machines: List[PublicMachineBrief] = Field(default_factory=list, max_length=5)
    machine_count_total: int

    total_quantity: int
    location_count_with_stock: int = 0

    # Availability status (derived from stock aggregates)
    availability_status: str  # IN_STOCK, LOW_STOCK, OUT_OF_STOCK

    # Primary location (or null)
    primary_location: Optional[PrimaryLocation] = None

    # Count of other active locations with stock
    other_locations_with_stock: int = 0
