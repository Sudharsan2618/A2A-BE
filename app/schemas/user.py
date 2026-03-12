"""
LuxeLife API — User schemas.

Request/response models for user endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """Public user profile returned by API."""

    id: str
    name: str
    email: str
    phone: str
    initials: str
    avatar: str | None = None
    location: str | None = None
    roles: list[str]
    active_role: str
    status: str
    kyc_progress: int
    created_at: datetime

    # Provider-specific
    specialization: str | None = None
    rating: float | None = None
    total_jobs: int | None = None

    # Owner-specific
    portfolio_value: str | None = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Fields a user can update on their own profile."""

    name: str | None = Field(None, min_length=2, max_length=100)
    location: str | None = Field(None, max_length=255)
    avatar: str | None = Field(None, max_length=512)
    fcm_token: str | None = Field(None, max_length=512)

    # Provider-specific
    specialization: str | None = Field(None, max_length=255)


class SwitchRoleRequest(BaseModel):
    """Switch the user's active role."""

    role: str = Field(
        ...,
        pattern=r"^(tenant|owner|provider|admin)$",
        description="Role to switch to (must be in user's roles list)",
    )


class UserListParams(BaseModel):
    """Query parameters for admin user listing."""

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    role: str | None = None
    status: str | None = None
    search: str | None = None
    sort: str = "-created_at"


def user_to_response(user) -> dict:
    """
    Convert a User ORM object to a response dict.

    Handles enum serialization and optional role-specific fields.
    """
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        initials=user.initials,
        avatar=user.avatar,
        location=user.location,
        roles=user.roles or [],
        active_role=user.active_role.value,
        status=user.status.value,
        kyc_progress=user.kyc_progress,
        created_at=user.created_at,
        specialization=user.specialization,
        rating=user.rating,
        total_jobs=user.total_jobs,
        portfolio_value=user.portfolio_value,
    ).model_dump()
