import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.notification import Notification
    from app.models.spare_part import SparePart
    from app.models.user import User


class SurplusKind(str, enum.Enum):
    SPARE_PART = "SPARE_PART"
    MATERIAL = "MATERIAL"
    MACHINERY = "MACHINERY"


class SurplusCondition(str, enum.Enum):
    NEW = "NEW"
    GOOD = "GOOD"
    USED = "USED"
    NEEDS_REPAIR = "NEEDS_REPAIR"


class SurplusStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    CLAIMED = "CLAIMED"
    WITHDRAWN = "WITHDRAWN"


class SurplusItem(Base):
    __tablename__ = "surplus_items"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('SPARE_PART', 'MATERIAL', 'MACHINERY')",
            name="ck_surplus_items_kind",
        ),
        CheckConstraint("quantity >= 0", name="ck_surplus_items_quantity"),
        CheckConstraint(
            "condition IN ('NEW', 'GOOD', 'USED', 'NEEDS_REPAIR')",
            name="ck_surplus_items_condition",
        ),
        CheckConstraint(
            "status IN ('AVAILABLE', 'RESERVED', 'CLAIMED', 'WITHDRAWN')",
            name="ck_surplus_items_status",
        ),
        Index("ix_surplus_items_status_location_id", "status", "location_id"),
        Index("ix_surplus_items_kind", "kind"),
        Index("ix_surplus_items_created_at", "created_at"),
        Index("ix_surplus_items_location_id", "location_id"),
        Index("ix_surplus_items_part_id", "part_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="units", server_default="units")
    condition: Mapped[str] = mapped_column(String(20), nullable=False)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    storage_details: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contact_note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    part_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("spare_parts.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SurplusStatus.AVAILABLE.value,
        server_default="AVAILABLE",
    )
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    location: Mapped["Location"] = relationship()
    part: Mapped[Optional["SparePart"]] = relationship()
    creator: Mapped["User"] = relationship()
    interests: Mapped[List["SurplusInterest"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="SurplusInterest.created_at.desc()",
    )
    notifications: Mapped[List["Notification"]] = relationship(back_populates="surplus_item")


class SurplusInterest(Base):
    __tablename__ = "surplus_interests"
    __table_args__ = (
        CheckConstraint("quantity_requested >= 1", name="ck_surplus_interests_quantity_requested"),
        UniqueConstraint("item_id", "user_id", name="uq_surplus_interests_item_user"),
        Index("ix_surplus_interests_item_id", "item_id"),
        Index("ix_surplus_interests_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("surplus_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    item: Mapped["SurplusItem"] = relationship(back_populates="interests")
    user: Mapped["User"] = relationship()

