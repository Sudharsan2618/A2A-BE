"""
LuxeLife API — Auth routes.

Handles registration, login, OTP, token refresh, and logout.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.core.security import decode_access_token
from app.database import get_db
from app.dependencies import bearer_scheme, get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SendOTPRequest,
    VerifyOTPRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user with email, phone, and password.

    Returns access/refresh tokens and user profile.
    """
    result = await AuthService.register(
        db,
        name=body.name,
        email=body.email,
        phone=body.phone,
        password=body.password,
        role=body.role,
    )
    return success_response(result)


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with email and password.

    Returns access/refresh tokens and user profile.
    """
    result = await AuthService.login(db, email=body.email, password=body.password)
    return success_response(result)


@router.post("/send-otp")
async def send_otp(body: SendOTPRequest):
    """
    Send a 6-digit OTP to the given phone number.

    Rate-limited to 5 requests per phone per hour.
    """
    result = await AuthService.send_otp(body.phone)
    return success_response(result)


@router.post("/verify-otp")
async def verify_otp(body: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Verify OTP and authenticate.

    Creates a new user if the phone number is not registered.
    """
    result = await AuthService.verify_otp(db, phone=body.phone, otp=body.otp)
    return success_response(result)


@router.post("/refresh")
async def refresh_tokens(
    body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """
    Exchange a refresh token for a new access/refresh token pair.

    The old refresh token is invalidated (rotation).
    """
    result = await AuthService.refresh_tokens(db, refresh_token=body.refresh_token)
    return success_response(result)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user),
                 credentials=Depends(bearer_scheme)):
    """
    Logout — blacklist the current access token.

    The token will be rejected until it naturally expires.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    jti = payload.get("jti", "")
    result = await AuthService.logout(access_token_jti=jti)
    return success_response(result)
