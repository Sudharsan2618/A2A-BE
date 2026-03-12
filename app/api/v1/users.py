"""
LuxeLife API — User routes.

Handles user profile and admin user management.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_roles
from app.core.responses import paginated_response, success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserUpdateRequest,
    user_to_response,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


# ── Current User ──

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return success_response(user_to_response(current_user))


@router.patch("/me")
async def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the current user's profile.

    Only provided (non-null) fields are updated.
    """
    result = await UserService.update_profile(
        db,
        current_user,
        name=body.name,
        location=body.location,
        avatar=body.avatar,
        fcm_token=body.fcm_token,
        specialization=body.specialization,
    )
    return success_response(result)


# ── Admin: User Management ──

@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("-created_at"),
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users with filtering, search, and pagination.

    **Admin only.**
    """
    items, total = await UserService.list_users(
        db,
        page=page,
        limit=limit,
        role=role,
        status=status,
        search=search,
        sort=sort,
    )
    return paginated_response(items, total, page, limit)


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get any user by ID. **Admin only.**"""
    user = await UserService.get_by_id(db, user_id)
    return success_response(user_to_response(user))


@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: str,
    new_status: str = Query(..., pattern=r"^(pending|awaiting_review|verified|suspended)$"),
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's account status. **Admin only.**"""
    result = await UserService.update_status(db, user_id, new_status=new_status)
    return success_response(result)
