"""Pydantic schemas for authentication requests, token responses, and user profiles."""
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    """Credentials payload for login via employee ID or email."""

    identifier: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Employee ID (e.g. ITCADM001) or Email address",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Account password",
    )


class LocationBrief(BaseModel):
    """Minimal location information nested within the current user profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class CurrentUser(BaseModel):
    """Public authenticated user profile with location details. Excludes password_hash and internals."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    name: str
    email: str
    role: UserRole
    location: LocationBrief


class TokenResponse(BaseModel):
    """Bearer access token payload returned upon successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: CurrentUser

