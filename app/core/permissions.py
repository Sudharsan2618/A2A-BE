"""
LuxeLife API — Role-based access control (RBAC).

Provides FastAPI dependencies that enforce role requirements.
"""

from fastapi import Depends

from app.dependencies import get_current_user
from app.core.exceptions import ForbiddenError
from app.models.user import User


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory that restricts access to specific roles.

    Usage:
        @router.get("/admin/dashboard")
        async def admin_dashboard(user: User = Depends(require_roles("admin"))):
            ...
    """

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.active_role.value not in allowed_roles:
            raise ForbiddenError(
                f"This action requires one of: {', '.join(allowed_roles)}"
            )
        return current_user

    return _check_role
