"""
LuxeLife API — SQLAlchemy base model and shared mixins.

Every model inherits from Base and optionally TimestampMixin.
IDs use CUID2 for URL-safe, collision-resistant, sortable identifiers.
"""

from datetime import datetime

from cuid2 import cuid_wrapper
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# CUID2 generator — produces 24-char IDs like "clx3b0v0k0000..."
generate_cuid = cuid_wrapper()


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class TimestampMixin:
    """Adds created_at / updated_at columns to any model."""

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )
