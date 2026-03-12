"""
LuxeLife API — Notification model.

Stores in-app notifications for payments, maintenance, inspections, etc.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, generate_cuid


class Notification(Base):
    """An in-app notification for a user."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=generate_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50))  # payment, maintenance, inspection
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(500))
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unread: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    action_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_target: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)

    user = relationship("User", backref="notifications")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type} unread={self.unread}>"
