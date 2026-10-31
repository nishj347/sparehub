from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PartMachine(Base):
    __tablename__ = "part_machines"

    part_id: Mapped[int] = mapped_column(
        ForeignKey("spare_parts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"),
        primary_key=True,
    )

