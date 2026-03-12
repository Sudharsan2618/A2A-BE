"""
LuxeLife API — KYC document model.

Tracks identity verification documents (Aadhaar, PAN, passport).
"""

import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, generate_cuid


class KycStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class KycDocument(Base, TimestampMixin):
    """A KYC verification document uploaded by a user."""

    __tablename__ = "kyc_documents"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=generate_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    doc_type: Mapped[str] = mapped_column(String(50))  # aadhaar, pan, passport
    file_url: Mapped[str] = mapped_column(String(512))
    status: Mapped[KycStatus] = mapped_column(
        Enum(KycStatus, name="kyc_status_enum", create_constraint=True),
        default=KycStatus.PENDING,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user = relationship("User", backref="kyc_documents")

    def __repr__(self) -> str:
        return f"<KycDocument id={self.id} type={self.doc_type} status={self.status.value}>"
