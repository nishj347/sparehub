from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inventory_transaction import InventoryTransaction
    from app.models.surplus import SurplusItem
    from app.models.user import User


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "ix_notifications_recipient_is_read_created_at",
            "recipient_user_id",
            "is_read",
            "created_at",
        ),
        Index("ix_notifications_surplus_item_id", "surplus_item_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("inventory_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    surplus_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("surplus_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    recipient_user: Mapped["User"] = relationship(back_populates="notifications")
    transaction: Mapped[Optional["InventoryTransaction"]] = relationship(
        back_populates="notifications"
    )
    surplus_item: Mapped[Optional["SurplusItem"]] = relationship(
        back_populates="notifications"
    )

