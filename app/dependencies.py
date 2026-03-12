"""
LuxeLife API — Shared FastAPI dependencies.

Contains the get_current_user dependency that extracts and validates
the JWT token from the Authorization header.
"""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.redis import redis_client

# HTTP Bearer scheme — extracts token from "Authorization: Bearer <token>"
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that authenticates the current request.

    1. Extracts the Bearer token from the Authorization header.
    2. Decodes the JWT and validates its signature + expiry.
    3. Checks if the token has been blacklisted (logout).
    4. Loads the user from the database.
    5. Returns the User ORM object.

    Raises UnauthorizedError if any step fails.
    """
    if credentials is None:
        raise UnauthorizedError("Missing authorization header")

    token = credentials.credentials

    # Decode JWT
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    user_id: str | None = payload.get("sub")
    jti: str | None = payload.get("jti")

    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    # Check if token is blacklisted (user logged out)
    if jti:
        is_blacklisted = await redis_client.get(f"blacklist:{jti}")
        if is_blacklisted:
            raise UnauthorizedError("Token has been revoked")

    # Load user from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedError("User not found")

    if user.status.value == "suspended":
        raise UnauthorizedError("Account has been suspended")

    return user
