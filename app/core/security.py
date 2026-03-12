"""
LuxeLife API — Security utilities.

Handles JWT token creation/verification, password hashing, and OTP generation.
All crypto operations use industry-standard libraries (jose, passlib, secrets).
"""

import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password Hashing ──

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


# ── JWT Tokens ──

def create_access_token(user_id: str, role: str) -> str:
    """
    Create a short-lived access token (default: 15 min).

    Payload contains:
    - sub: user ID
    - role: active role at time of token creation
    - type: "access" (to distinguish from refresh tokens)
    - jti: unique token ID (for blacklisting on logout)
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    """
    Create a long-lived refresh token (default: 30 days).

    Contains only the user ID and a unique jti for rotation tracking.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token.

    Raises JWTError on invalid/expired tokens.
    """
    payload = jwt.decode(
        token, settings.JWT_ACCESS_SECRET, algorithms=["HS256"]
    )
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict:
    """
    Decode and validate a refresh token.

    Raises JWTError on invalid/expired tokens.
    """
    payload = jwt.decode(
        token, settings.JWT_REFRESH_SECRET, algorithms=["HS256"]
    )
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")
    return payload


# ── OTP ──

def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically secure numeric OTP."""
    return "".join(secrets.choice("0123456789") for _ in range(length))
