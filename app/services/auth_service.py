"""
LuxeLife API — Auth service.

Business logic for registration, login, OTP, and token management.
All database operations use the async session passed in — no session
creation inside the service layer for proper lifecycle control.
"""

from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    RateLimitedError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_otp,
    hash_password,
    verify_password,
)
from app.models import generate_cuid
from app.models.user import Role, User, UserStatus
from app.redis import redis_client
from app.schemas.user import user_to_response

# ── Constants ──
OTP_TTL_SECONDS = 300       # 5 minutes
OTP_RATE_LIMIT = 5          # max per phone per hour
TOKEN_BLACKLIST_TTL = 900   # 15 min (match access token expiry)


class AuthService:
    """Handles all authentication business logic."""

    # ── Registration ──

    @staticmethod
    async def register(
        db: AsyncSession,
        *,
        name: str,
        email: str,
        phone: str,
        password: str,
        role: str,
    ) -> dict:
        """
        Create a new user account.

        - Checks for duplicate email/phone.
        - Hashes password with bcrypt.
        - Generates initials from name.
        - Returns tokens + user profile.
        """
        # Check duplicates
        existing = await db.execute(
            select(User).where((User.email == email) | (User.phone == phone))
        )
        if existing.scalar_one_or_none():
            raise ConflictError("A user with this email or phone already exists")

        # Build user
        initials = "".join(
            word[0].upper() for word in name.split()[:2]
        ) or name[:2].upper()

        user = User(
            id=generate_cuid(),
            name=name,
            email=email,
            phone=phone,
            password_hash=hash_password(password),
            initials=initials,
            roles=[role],
            active_role=Role(role),
            status=UserStatus.PENDING,
        )
        db.add(user)
        await db.flush()  # get the ID without committing (commit in get_db)

        # Generate tokens
        tokens = _create_token_pair(user)

        return {
            "tokens": tokens,
            "user": user_to_response(user),
            "is_new": True,
        }

    # ── Email + Password Login ──

    @staticmethod
    async def login(
        db: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> dict:
        """
        Authenticate via email + password.

        - Finds user by email.
        - Verifies bcrypt password hash.
        - Updates last_login_at timestamp.
        - Returns tokens + user profile.
        """
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        if user.status == UserStatus.SUSPENDED:
            raise UnauthorizedError("Account has been suspended")

        # Update login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()

        tokens = _create_token_pair(user)

        return {
            "tokens": tokens,
            "user": user_to_response(user),
            "is_new": False,
        }

    # ── OTP ──

    @staticmethod
    async def send_otp(phone: str) -> dict:
        """
        Generate and send a 6-digit OTP via Twilio.

        - Rate-limited to 5 requests per phone per hour.
        - OTP is stored in Redis with a 5-minute TTL.
        """
        # Rate limit check
        rate_key = f"otp_rate:{phone}"
        count = await redis_client.get(rate_key)
        if count and int(count) >= OTP_RATE_LIMIT:
            raise RateLimitedError("Too many OTP requests. Try again later.")

        otp = generate_otp()

        # Store OTP in Redis
        await redis_client.setex(f"otp:{phone}", OTP_TTL_SECONDS, otp)

        # Increment rate counter (1-hour window)
        pipe = redis_client.pipeline()
        await pipe.incr(rate_key)
        await pipe.expire(rate_key, 3600)
        await pipe.execute()

        # Send via Twilio
        try:
            from app.services.sms_service import SMSService
            SMSService.send_otp(phone, otp)
        except Exception:
            # In development, log OTP to console if Twilio is not configured
            if settings.DEBUG:
                print(f"[DEV OTP] {phone} → {otp}")
            else:
                raise

        return {"message": "OTP sent successfully", "expires_in": OTP_TTL_SECONDS}

    @staticmethod
    async def verify_otp(db: AsyncSession, *, phone: str, otp: str) -> dict:
        """
        Verify an OTP and return tokens.

        - Checks Redis for the stored OTP.
        - Creates user if not exists (phone-based signup).
        - Returns tokens + user profile.
        """
        stored_otp = await redis_client.get(f"otp:{phone}")

        if not stored_otp or stored_otp != otp:
            raise BadRequestError("Invalid or expired OTP")

        # Delete OTP after successful verification
        await redis_client.delete(f"otp:{phone}")

        # Find or create user
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        is_new = False

        if not user:
            # Auto-create user on first OTP login
            is_new = True
            user = User(
                id=generate_cuid(),
                name="LuxeLife User",
                email=f"{phone.replace('+', '')}@placeholder.luxelife.app",
                phone=phone,
                password_hash=hash_password(generate_otp(32)),  # random password
                initials="LU",
                roles=["tenant"],
                active_role=Role.TENANT,
                status=UserStatus.PENDING,
            )
            db.add(user)
            await db.flush()

        # Update login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()

        tokens = _create_token_pair(user)

        return {
            "tokens": tokens,
            "user": user_to_response(user),
            "is_new": is_new,
        }

    # ── Token Refresh ──

    @staticmethod
    async def refresh_tokens(db: AsyncSession, *, refresh_token: str) -> dict:
        """
        Exchange a refresh token for a new token pair.

        - Validates the refresh token.
        - Blacklists the old refresh token's jti (rotation).
        - Returns new access + refresh tokens.
        """
        try:
            payload = decode_refresh_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("Invalid or expired refresh token")

        user_id = payload.get("sub")
        old_jti = payload.get("jti")

        # Check if the old refresh token was already used (replay attack)
        if old_jti:
            already_used = await redis_client.get(f"rt_used:{old_jti}")
            if already_used:
                # Potential token theft — blacklist all tokens for this user
                raise UnauthorizedError("Refresh token has already been used")

            # Mark old refresh token as used
            await redis_client.setex(
                f"rt_used:{old_jti}",
                settings.JWT_REFRESH_EXPIRE_DAYS * 86400,
                "1",
            )

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedError("User not found")

        tokens = _create_token_pair(user)

        return {"tokens": tokens, "user": user_to_response(user)}

    # ── Logout ──

    @staticmethod
    async def logout(*, access_token_jti: str) -> dict:
        """
        Blacklist the current access token's jti in Redis.

        The token remains invalid until it naturally expires.
        """
        await redis_client.setex(
            f"blacklist:{access_token_jti}",
            TOKEN_BLACKLIST_TTL,
            "1",
        )
        return {"message": "Logged out successfully"}


# ── Private Helpers ──

def _create_token_pair(user: User) -> dict:
    """Generate an access + refresh token pair for a user."""
    return {
        "access_token": create_access_token(user.id, user.active_role.value),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }
