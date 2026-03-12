"""
LuxeLife API — Property routes.

Handles property browsing, CRUD, owner/tenant views.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_roles
from app.core.responses import paginated_response, success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["Properties"])


# ── Browse & Search ──

@router.get("")
async def search_properties(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search name, address, city"),
    city: str | None = Query(None),
    type: str | None = Query(None),
    furnishing: str | None = Query(None),
    occupancy: str | None = Query(None),
    min_rent: int | None = Query(None, ge=0),
    max_rent: int | None = Query(None),
    bhk: str | None = Query(None),
    premium: bool | None = Query(None),
    sort: str = Query("-created_at"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Browse and search properties with filters.

    Supports filtering by city, type, furnishing, occupancy, rent range, BHK, and premium.
    """
    items, total = await PropertyService.search(
        db,
        page=page,
        limit=limit,
        search=search,
        city=city,
        type=type,
        furnishing=furnishing,
        occupancy=occupancy,
        min_rent=min_rent,
        max_rent=max_rent,
        bhk=bhk,
        premium=premium,
        sort=sort,
    )
    return paginated_response(items, total, page, limit)


@router.get("/owner/me")
async def get_my_properties(
    user: User = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get all properties owned by the current user."""
    items = await PropertyService.get_owner_properties(db, user.id)
    return success_response(items)


@router.get("/tenant/me")
async def get_my_rented_properties(
    user: User = Depends(require_roles("tenant")),
    db: AsyncSession = Depends(get_db),
):
    """Get properties where the current user is a tenant."""
    items = await PropertyService.get_tenant_property(db, user.id)
    return success_response(items)


# ── CRUD ──

@router.get("/{property_id}")
async def get_property(
    property_id: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get property details by ID."""
    result = await PropertyService.get_by_id(db, property_id)
    return success_response(result)


@router.post("", status_code=201)
async def create_property(
    body: PropertyCreate,
    user: User = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new property listing. **Owner/Admin only.**"""
    result = await PropertyService.create(db, user, **body.model_dump())
    return success_response(result)


@router.patch("/{property_id}")
async def update_property(
    property_id: str,
    body: PropertyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a property. Only the owner or admin can update."""
    data = body.model_dump(exclude_none=True)
    result = await PropertyService.update(db, property_id, user, **data)
    return success_response(result)


@router.delete("/{property_id}")
async def delete_property(
    property_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a property. Only the owner or admin can delete."""
    result = await PropertyService.delete(db, property_id, user)
    return success_response(result)
