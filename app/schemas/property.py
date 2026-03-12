"""
LuxeLife API — Property schemas.

Request/response models for property endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PropertyCreate(BaseModel):
    """Create a new property listing."""

    name: str = Field(..., min_length=2, max_length=200, examples=["Serenity Heights"])
    unit: str = Field(..., max_length=50, examples=["Apt 4B"])
    address: str = Field(..., max_length=500, examples=["123 Marine Drive"])
    city: str = Field(..., max_length=100, examples=["Mumbai"])
    state: str = Field(..., max_length=100, examples=["Maharashtra"])
    pincode: str = Field(..., pattern=r"^\d{6}$", examples=["400001"])
    type: str = Field(..., pattern=r"^(apartment|villa|independent_house|penthouse)$")
    bhk: str = Field(..., max_length=20, examples=["3 BHK"])
    sqft: int = Field(..., gt=0, examples=[1200])
    furnishing: str = Field(
        ..., pattern=r"^(fully_furnished|semi_furnished|unfurnished)$"
    )
    floor: int = Field(..., ge=0, examples=[4])
    total_floors: int = Field(..., gt=0, examples=[12])
    facing: str | None = Field(None, max_length=50, examples=["East"])
    rent: int = Field(..., gt=0, description="Monthly rent in INR", examples=[35000])
    security_deposit: int = Field(..., ge=0, examples=[10500000])
    maintenance_charges: int = Field(..., ge=0, examples=[300000])
    description: str | None = Field(None, max_length=2000)
    premium: bool = False
    amenities: list[str] = Field(default=[], examples=[["parking", "gym", "pool"]])
    images: list[str] = Field(default=[], description="GCS URLs for property images")


class PropertyUpdate(BaseModel):
    """Partial update for a property."""

    name: str | None = Field(None, min_length=2, max_length=200)
    address: str | None = Field(None, max_length=500)
    rent: int | None = Field(None, gt=0)
    security_deposit: int | None = Field(None, ge=0)
    maintenance_charges: int | None = Field(None, ge=0)
    description: str | None = None
    furnishing: str | None = None
    amenities: list[str] | None = None
    images: list[str] | None = None
    premium: bool | None = None
    occupancy: str | None = Field(None, pattern=r"^(occupied|vacant)$")
    tenant_id: str | None = None
    lease_start: datetime | None = None
    lease_end: datetime | None = None


class PropertyResponse(BaseModel):
    """Property detail returned by API."""

    id: str
    name: str
    unit: str
    address: str
    city: str
    state: str
    pincode: str
    type: str
    bhk: str
    sqft: int
    furnishing: str
    floor: int
    total_floors: int
    facing: str | None = None
    rent: int
    security_deposit: int
    maintenance_charges: int
    description: str | None = None
    images: list[str] = []
    occupancy: str
    premium: bool
    amenities: list = []
    lease_start: datetime | None = None
    lease_end: datetime | None = None
    owner_id: str
    tenant_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def property_to_response(prop) -> dict:
    """Convert a Property ORM object to a response dict."""
    return PropertyResponse(
        id=prop.id,
        name=prop.name,
        unit=prop.unit,
        address=prop.address,
        city=prop.city,
        state=prop.state,
        pincode=prop.pincode,
        type=prop.type.value,
        bhk=prop.bhk,
        sqft=prop.sqft,
        furnishing=prop.furnishing.value,
        floor=prop.floor,
        total_floors=prop.total_floors,
        facing=prop.facing,
        rent=prop.rent,
        security_deposit=prop.security_deposit,
        maintenance_charges=prop.maintenance_charges,
        description=prop.description,
        images=prop.images or [],
        occupancy=prop.occupancy.value,
        premium=prop.premium,
        amenities=prop.amenities or [],
        lease_start=prop.lease_start,
        lease_end=prop.lease_end,
        owner_id=prop.owner_id,
        tenant_id=prop.tenant_id,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
    ).model_dump()
