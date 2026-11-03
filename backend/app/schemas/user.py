"""Schemas for Admin User / Employee management."""
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import UserRole

EMPLOYEE_ID_REGEX = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,31}$")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserLocationBrief(BaseModel):
    """Brief location reference embedded in user responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class UserRead(BaseModel):
    """Admin-facing user response schema. Never exposes password hash or internal lock fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    name: str
    email: str
    role: UserRole
    location: UserLocationBrief
    is_active: bool
    is_locked: bool = False
    created_at: datetime


class UserCreate(BaseModel):
    """Schema for creating a new user by an admin."""

    employee_id: str = Field(..., description="Unique employee ID (3-32 chars, alphanumeric, _ or -)")
    name: str = Field(..., min_length=2, max_length=100, description="Full name of employee")
    email: str = Field(..., max_length=255, description="Unique email address")
    role: UserRole = Field(default=UserRole.EMPLOYEE, description="User role (EMPLOYEE or STORE_ADMIN)")
    location_id: int = Field(..., description="Active location ID")
    password: str = Field(..., min_length=12, max_length=128, description="Initial temporary password")

    @field_validator("employee_id")
    @classmethod
    def validate_employee_id(cls, v: str) -> str:
        clean = v.strip().upper()
        if not EMPLOYEE_ID_REGEX.match(clean):
            raise ValueError(
                "Employee ID must be 3-32 characters, start with an alphanumeric character, and contain only letters, numbers, hyphens or underscores."
            )
        return clean

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format.")
        return clean

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = " ".join(v.strip().split())
        if len(clean) < 2 or len(clean) > 100:
            raise ValueError("Name must be between 2 and 100 characters.")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or all-whitespace.")
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long.")
        if len(v) > 128:
            raise ValueError("Password cannot exceed 128 characters.")
        return v


class UserUpdate(BaseModel):
    """Schema for updating an existing user (employee_id is immutable)."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    location_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = " ".join(v.strip().split())
        if len(clean) < 2 or len(clean) > 100:
            raise ValueError("Name must be between 2 and 100 characters.")
        return clean

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format.")
        return clean


class UserPasswordReset(BaseModel):
    """Schema for administrative password reset."""

    password: str = Field(..., min_length=12, max_length=128, description="New password")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or all-whitespace.")
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long.")
        if len(v) > 128:
            raise ValueError("Password cannot exceed 128 characters.")
        return v

