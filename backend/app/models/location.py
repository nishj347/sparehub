from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inventory import Inventory
    from app.models.inventory_transaction import InventoryTransaction
    from app.models.machine import Machine
    from app.models.user import User


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="location")
    machines: Mapped[List["Machine"]] = relationship(back_populates="location")
    inventory_items: Mapped[List["Inventory"]] = relationship(back_populates="location")
    transactions: Mapped[List["InventoryTransaction"]] = relationship(back_populates="location")

