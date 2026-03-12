"""
LuxeLife API — Agreement model.

Represents a rental agreement between a tenant and a property owner.
Tracks the lifecycle: created → awaiting_signature → signed → active → terminated.
Links to the property, tenant, owner, and the advance/deposit payment.
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


class AgreementStatus(str, enum.Enum):
    DRAFT = "draft"
    AWAITING_PAYMENT = "awaiting_payment"
    AWAITING_SIGNATURE = "awaiting_signature"
    SIGNED = "signed"
    ACTIVE = "active"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class Agreement(Base, TimestampMixin):
    """A rental agreement between a tenant and property owner."""

    __tablename__ = "agreements"

    # ── Identity ──
    id: Mapped[str] = mapped_column(
        String(30), primary_key=True, default=generate_cuid
    )

    # ── Status ──
    status: Mapped[AgreementStatus] = mapped_column(
        Enum(
            AgreementStatus,
            name="agreement_status_enum",
            create_constraint=True,
            values_callable=lambda e: [s.value for s in e],
        ),
        default=AgreementStatus.DRAFT,
        index=True,
    )

    # ── Lease Terms ──
    rent_amount: Mapped[int] = mapped_column(Integer)  # monthly rent in INR
    security_deposit: Mapped[int] = mapped_column(Integer)  # total deposit in INR
    maintenance_charges: Mapped[int] = mapped_column(Integer, default=0)
    lease_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_duration_months: Mapped[int] = mapped_column(Integer, default=12)

    # ── Agreement Content ──
    terms_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_clauses: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Signatures ──
    tenant_signature: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )  # URL or base64 of signature image
    owner_signature: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    tenant_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── PDF ──
    pdf_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Foreign Keys ──
    property_id: Mapped[str] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    deposit_payment_id: Mapped[str | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relationships ──
    property = relationship("Property", backref="agreements")
    tenant = relationship("User", foreign_keys=[tenant_id], backref="tenant_agreements")
    owner = relationship("User", foreign_keys=[owner_id], backref="owner_agreements")
    deposit_payment = relationship("Payment", backref="agreement")

    def __repr__(self) -> str:
        return f"<Agreement id={self.id} status={self.status.value} property={self.property_id}>"
