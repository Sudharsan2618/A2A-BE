"""
LuxeLife API — Job (service request) model.

Represents a maintenance or service request raised by a tenant/owner
and assigned to a service provider.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, generate_cuid


class JobStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class Job(Base, TimestampMixin):
    """A service/maintenance request on the platform."""

    __tablename__ = "jobs"

    # ── Identity ──
    id: Mapped[str] = mapped_column(
        String(30), primary_key=True, default=generate_cuid
    )
    service_type: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(50), default="🔧")
    address: Mapped[str] = mapped_column(String(500))

    # ── People ──
    tenant_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Status & Schedule ──
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum", create_constraint=True),
        default=JobStatus.SCHEDULED,
        index=True,
    )
    scheduled_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estimated_cost: Mapped[dict] = mapped_column(JSONB, default=dict)  # {min, max}
    actual_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Work Report (JSONB) ──
    work_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Foreign Keys ──
    property_id: Mapped[str] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    provider_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ── Relationships ──
    property = relationship("Property", back_populates="jobs")

    def __repr__(self) -> str:
        return f"<Job id={self.id} type={self.service_type} status={self.status.value}>"
