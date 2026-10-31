"""Common schemas shared across business models."""
from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Generic paginated list envelope."""

    items: List[T]
    total: int = Field(..., ge=0, description="Total matching items across all pages")
    page: int = Field(..., ge=1, description="Current 1-based page number")
    page_size: int = Field(..., ge=1, le=100, description="Page size limit")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
