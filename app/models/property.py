"""
LuxeLife API — Property model.

Represents a residential property listed on the platform.
Supports different property types, furnishing levels, and occupancy states.
Amenities stored as JSONB for flexible querying.
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
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, generate_cuid


class PropertyType(str, enum.Enum):
    APARTMENT = "apartment"
    VILLA = "villa"
    INDEPENDENT_HOUSE = "independent_house"
    PENTHOUSE = "penthouse"


class Furnishing(str, enum.Enum):
    FULLY_FURNISHED = "fully_furnished"
    SEMI_FURNISHED = "semi_furnished"
    UNFURNISHED = "unfurnished"


class Occupancy(str, enum.Enum):
    OCCUPIED = "occupied"
    VACANT = "vacant"


class Property(Base, TimestampMixin):
    """A residential property listed on the LuxeLife platform."""

    __tablename__ = "properties"

    # ── Identity ──
    id: Mapped[str] = mapped_column(
        String(30), primary_key=True, default=generate_cuid
    )
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(50))

    # ── Location ──
    address: Mapped[str] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(100))
    pincode: Mapped[str] = mapped_column(String(10))

    # ── Details ──
    type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType, name="property_type_enum", create_constraint=True)
    )
    bhk: Mapped[str] = mapped_column(String(20))
    sqft: Mapped[int] = mapped_column(Integer)
    furnishing: Mapped[Furnishing] = mapped_column(
        Enum(Furnishing, name="furnishing_enum", create_constraint=True)
    )
    floor: Mapped[int] = mapped_column(Integer)
    total_floors: Mapped[int] = mapped_column(Integer)
    facing: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Financials (stored in INR) ──
    rent: Mapped[int] = mapped_column(Integer, index=True)
    security_deposit: Mapped[int] = mapped_column(Integer)
    maintenance_charges: Mapped[int] = mapped_column(Integer)

    # ── Description & Media ──
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[list] = mapped_column(ARRAY(String), default=list)

    # ── Status ──
    occupancy: Mapped[Occupancy] = mapped_column(
        Enum(Occupancy, name="occupancy_enum", create_constraint=True),
        default=Occupancy.VACANT,
        index=True,
    )
    premium: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Amenities (JSONB for flexible storage) ──
    amenities: Mapped[list] = mapped_column(JSONB, default=list)

    # ── Lease Info ──
    lease_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Foreign Keys ──
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ── Relationships ──
    owner = relationship(
        "User", foreign_keys=[owner_id], backref="owned_properties"
    )
    tenant = relationship(
        "User", foreign_keys=[tenant_id], backref="tenant_properties"
    )
    payments = relationship("Payment", back_populates="property")
    jobs = relationship("Job", back_populates="property")

    def __repr__(self) -> str:
        return f"<Property id={self.id} name={self.name} city={self.city}>"
