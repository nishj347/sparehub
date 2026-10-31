from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inventory import Inventory
    from app.models.inventory_transaction import InventoryTransaction
    from app.models.machine import Machine


class SparePart(Base):
    __tablename__ = "spare_parts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    specifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    machines: Mapped[List["Machine"]] = relationship(
        secondary="part_machines",
        back_populates="spare_parts",
    )
    inventory_items: Mapped[List["Inventory"]] = relationship(back_populates="part")
    transactions: Mapped[List["InventoryTransaction"]] = relationship(back_populates="part")

