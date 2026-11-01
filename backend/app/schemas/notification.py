"""Pydantic schemas for Admin In-App Notifications (Module 9A)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NotificationItem(BaseModel):
    id: int
    message: str
    is_read: bool
    created_at: datetime
    transaction_id: Optional[int] = None
    part_id: Optional[int] = None
    part_name: Optional[str] = None
    quantity: Optional[int] = None  # Positive units issued
    actor_employee_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    unread: int = Field(..., ge=0, description="Total unread notifications for caller")


class ReadAllResponse(BaseModel):
    updated: int = Field(..., ge=0, description="Number of notifications marked as read")

