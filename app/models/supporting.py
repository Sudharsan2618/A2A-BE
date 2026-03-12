"""
LuxeLife API — Dispute, BankAccount, Message, AuditLog models.

Supporting models for the platform's financial, messaging, and audit features.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, generate_cuid


class Dispute(Base, TimestampMixin):
    """A dispute raised against a job."""

    __tablename__ = "disputes"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=generate_cuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    raised_by: Mapped[str] = mapped_column(String(30))  # user ID
    reason: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, in_review, resolved, escalated
    resolution: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job = relationship("Job", backref="dispute")

    def __repr__(self) -> str:
        return f"<Dispute id={self.id} status={self.status}>"


class BankAccount(Base, TimestampMixin):
    """A user's bank account for payouts."""

    __tablename__ = "bank_accounts"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=generate_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_name: Mapped[str] = mapped_column(String(100))
    account_number: Mapped[str] = mapped_column(String(30))
    ifsc_code: Mapped[str] = mapped_column(String(20))
    bank_name: Mapped[str] = mapped_column(String(100))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", backref="bank_accounts")

    def __repr__(self) -> str:
        return f"<BankAccount id={self.id} bank={self.bank_name}>"


class Message(Base):
    """A chat message between users."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=generate_cuid)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    receiver_id: Mapped[str] = mapped_column(String(30))
    channel_id: Mapped[str] = mapped_column(String(60), index=True)
    content: Mapped[str] = mapped_column(String(2000))
    content_type: Mapped[str] = mapped_column(String(20), default="text")  # text, image, file
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    def __repr__(self) -> str:
        return f"<Message id={self.id} channel={self.channel_id}>"


class AuditLog(Base):
    """Immutable audit trail for sensitive operations."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=generate_cuid)
    user_id: Mapped[str] = mapped_column(String(30), index=True)
    action: Mapped[str] = mapped_column(String(100))  # e.g. "payment.created"
    entity_type: Mapped[str] = mapped_column(String(50))  # e.g. "Payment"
    entity_id: Mapped[str] = mapped_column(String(30))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action}>"
