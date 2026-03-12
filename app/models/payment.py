"""
LuxeLife API — Payment model.

Tracks rent payments, service payments, and security deposits.
Integrates with Razorpay for order management and signature verification.
All monetary amounts are stored in INR as whole numbers.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, generate_cuid


class PaymentType(str, enum.Enum):
    RENT = "rent"
    SERVICE = "service"
    SECURITY_DEPOSIT = "security_deposit"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    OVERDUE = "overdue"
    PAID = "paid"
    ESCROWED = "escrowed"
    REFUNDED = "refunded"
    FAILED = "failed"


class PaymentMethod(str, enum.Enum):
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    WALLET = "wallet"


class Payment(Base, TimestampMixin):
    """A financial transaction on the LuxeLife platform."""

    __tablename__ = "payments"

    # ── Identity ──
    id: Mapped[str] = mapped_column(
        String(30), primary_key=True, default=generate_cuid
    )
    type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, name="payment_type_enum", create_constraint=True)
    )
    label: Mapped[str] = mapped_column(String(200))
    amount: Mapped[int] = mapped_column(Integer)  # in INR

    # ── Breakdown (JSONB for flexibility) ──
    # e.g. {"rent": 3500000, "maintenance": 300000}
    # or   {"materials": 150000, "labor": 100000}
    breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)

    # ── Status ──
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", create_constraint=True),
        default=PaymentStatus.PENDING,
        index=True,
    )

    # ── Dates ──
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    paid_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Payment Method & Gateway ──
    method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum", create_constraint=True),
        nullable=True,
    )
    reference_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # gateway transaction ID
    razorpay_order_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # ── Payout tracking ──
    payout_processed: Mapped[bool] = mapped_column(Boolean, default=False)

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
    provider_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relationships ──
    property = relationship("Property", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} type={self.type.value} status={self.status.value} amount={self.amount}>"
