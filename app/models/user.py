"""
LuxeLife API — User model.

Supports multi-role users (a single person can be both a tenant and an owner).
The active_role field tracks which role they are currently operating as.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, generate_cuid


class Role(str, enum.Enum):
    """User roles in the system."""
    TENANT = "tenant"
    OWNER = "owner"
    PROVIDER = "provider"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    """KYC / account verification status."""
    PENDING = "pending"
    AWAITING_REVIEW = "awaiting_review"
    VERIFIED = "verified"
    SUSPENDED = "suspended"


class User(Base, TimestampMixin):
    """Core user entity — shared across all roles."""

    __tablename__ = "users"

    # ── Identity ──
    id: Mapped[str] = mapped_column(
        String(30), primary_key=True, default=generate_cuid
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(100))
    initials: Mapped[str] = mapped_column(String(4))
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Role & Status ──
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=lambda: ["tenant"]
    )
    active_role: Mapped[Role] = mapped_column(
        Enum(Role, name="role_enum", create_constraint=True),
        default=Role.TENANT,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status_enum", create_constraint=True),
        default=UserStatus.PENDING,
        index=True,
    )
    kyc_progress: Mapped[int] = mapped_column(Integer, default=0)

    # ── Provider-specific ──
    specialization: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_jobs: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Owner-specific ──
    portfolio_value: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    # ── Device & Auth ──
    fcm_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships (defined in future models) ──
    # owned_properties, tenant_properties, kyc_documents, bank_accounts,
    # notifications, etc. will be added as those models are created.

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.active_role.value}>"
