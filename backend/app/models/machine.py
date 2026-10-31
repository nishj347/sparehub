from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.spare_part import SparePart


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


    # Relationships
    location: Mapped[Optional["Location"]] = relationship(back_populates="machines")
    spare_parts: Mapped[List["SparePart"]] = relationship(
        secondary="part_machines",
        back_populates="machines",
    )

