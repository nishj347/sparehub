from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TransactionType

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.notification import Notification
    from app.models.spare_part import SparePart
    from app.models.user import User


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        CheckConstraint("quantity_change <> 0", name="quantity_change_not_zero"),
        CheckConstraint("quantity_after >= 0", name="quantity_after_non_negative"),
        CheckConstraint(
            "transaction_type <> 'ISSUED' OR quantity_change < 0",
            name="issued_negative",
        ),
        CheckConstraint(
            "transaction_type <> 'RECEIVED' OR quantity_change > 0",
            name="received_positive",
        ),
        Index("ix_inventory_transactions_part_id_location_id", "part_id", "location_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(
        ForeignKey("spare_parts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(
            TransactionType,
            native_enum=False,
            create_constraint=True,
            name="inventory_transactions_type_check",
            length=20,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    # Relationships
    part: Mapped["SparePart"] = relationship(back_populates="transactions")
    location: Mapped["Location"] = relationship(back_populates="transactions")
    user: Mapped[Optional["User"]] = relationship(back_populates="transactions")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="transaction")

