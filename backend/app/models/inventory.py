from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.spare_part import SparePart


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("part_id", "location_id", name="uq_inventory_part_id_location_id"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("min_stock_level >= 0", name="min_stock_level_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(
        ForeignKey("spare_parts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    store_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rack: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bin: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    min_stock_level: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    part: Mapped["SparePart"] = relationship(back_populates="inventory_items")
    location: Mapped["Location"] = relationship(back_populates="inventory_items")

