"""
LuxeLife API — Inspection model.

Tracks move-in, move-out, and periodic property inspections.
Room-level data and settlement details stored as JSONB.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, generate_cuid


class InspectionType(str, enum.Enum):
    MOVE_IN = "move_in"
    MOVE_OUT = "move_out"
    PERIODIC = "periodic"


class InspectionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISPUTED = "disputed"


class Inspection(Base, TimestampMixin):
    """A property inspection record."""

    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=generate_cuid)
    type: Mapped[InspectionType] = mapped_column(
        Enum(InspectionType, name="inspection_type_enum", create_constraint=True)
    )
    status: Mapped[InspectionStatus] = mapped_column(
        Enum(InspectionStatus, name="inspection_status_enum", create_constraint=True),
        default=InspectionStatus.SCHEDULED,
        index=True,
    )
    scheduled_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tenant_name: Mapped[str] = mapped_column(String(100))
    inspector_id: Mapped[str] = mapped_column(String(30))
    rooms: Mapped[list] = mapped_column(JSONB, default=list)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    settlement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    property_id: Mapped[str] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    property = relationship("Property", backref="inspections")

    def __repr__(self) -> str:
        return f"<Inspection id={self.id} type={self.type.value} status={self.status.value}>"
