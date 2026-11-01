import re
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.surplus import SurplusCondition, SurplusKind, SurplusStatus


def strip_control_chars(v: Optional[str]) -> Optional[str]:
    """Strip dangerous ASCII control characters while preserving printable text."""
    if v is None:
        return None
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v).strip()
    return cleaned if cleaned else None


def clean_required_string(v: str) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v).strip()
    if not cleaned:
        raise ValueError("Field cannot be empty or whitespace only.")
    return cleaned


class SurplusLocationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str


class SurplusPartSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    part_number: str
    name: str


class MyInterestSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    quantity_requested: int
    message: Optional[str] = None


class SurplusItemList(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    kind: SurplusKind
    condition: SurplusCondition
    quantity: int
    unit: str
    status: SurplusStatus
    image_url: Optional[str] = None
    location: SurplusLocationSummary
    storage_details: Optional[str] = None
    valid_until: Optional[date] = None
    part: Optional[SurplusPartSummary] = None
    is_my_location: bool
    listed_at: datetime
    my_interest: Optional[MyInterestSummary] = None


class SurplusUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    employee_id: str


class SurplusItemDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    kind: SurplusKind
    condition: SurplusCondition
    quantity: int
    unit: str
    status: SurplusStatus
    image_url: Optional[str] = None
    location: SurplusLocationSummary
    storage_details: Optional[str] = None
    valid_until: Optional[date] = None
    part: Optional[SurplusPartSummary] = None
    is_my_location: bool
    listed_at: datetime
    description: Optional[str] = None
    contact_note: Optional[str] = None
    listed_by: SurplusUserSummary
    my_interest: Optional[MyInterestSummary] = None


class SurplusFiltersResponse(BaseModel):
    kinds: List[str]
    conditions: List[str]
    locations: List[SurplusLocationSummary]


class SurplusInterestCreate(BaseModel):
    quantity_requested: int = Field(..., ge=1)
    message: Optional[str] = Field(None, max_length=500)

    @field_validator("message")
    @classmethod
    def clean_message(cls, v: Optional[str]) -> Optional[str]:
        return strip_control_chars(v)


class SurplusInterestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_id: int
    quantity_requested: int
    message: Optional[str] = None
    created_at: datetime


class MySurplusInterestItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quantity_requested: int
    message: Optional[str] = None
    created_at: datetime
    item: SurplusItemList


class AdminInterestUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    employee_id: str
    location: SurplusLocationSummary


class AdminSurplusInterestRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user: AdminInterestUserSummary
    quantity_requested: int
    message: Optional[str] = None
    created_at: datetime


class SurplusItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    kind: SurplusKind
    quantity: int = Field(..., ge=0)
    unit: str = Field("units", min_length=1, max_length=20)
    condition: SurplusCondition
    location_id: int = Field(..., ge=1)
    description: Optional[str] = None
    storage_details: Optional[str] = Field(None, max_length=200)
    contact_note: Optional[str] = Field(None, max_length=200)
    part_id: Optional[int] = None
    valid_until: Optional[date] = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        return clean_required_string(v)

    @field_validator("unit")
    @classmethod
    def clean_unit(cls, v: str) -> str:
        return clean_required_string(v)

    @field_validator("description", "storage_details", "contact_note")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        return strip_control_chars(v)


class SurplusItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    kind: Optional[SurplusKind] = None
    quantity: Optional[int] = Field(None, ge=0)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    condition: Optional[SurplusCondition] = None
    location_id: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    storage_details: Optional[str] = Field(None, max_length=200)
    contact_note: Optional[str] = Field(None, max_length=200)
    part_id: Optional[int] = None
    valid_until: Optional[date] = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: Optional[str]) -> Optional[str]:
        return clean_required_string(v) if v is not None else None

    @field_validator("unit")
    @classmethod
    def clean_unit(cls, v: Optional[str]) -> Optional[str]:
        return clean_required_string(v) if v is not None else None

    @field_validator("description", "storage_details", "contact_note")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        return strip_control_chars(v)


class SurplusStatusUpdate(BaseModel):
    status: SurplusStatus

