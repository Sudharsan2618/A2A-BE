"""
LuxeLife API — Auth schemas.

Request/response models for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field


# ── Requests ──

class RegisterRequest(BaseModel):
    """Account registration via email + password."""
    name: str = Field(..., min_length=2, max_length=100, examples=["Rajesh Mehta"])
    email: EmailStr = Field(..., examples=["rajesh@example.com"])
    phone: str = Field(
        ...,
        pattern=r"^\+\d{10,15}$",
        examples=["+919876543210"],
        description="Phone number in E.164 format",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["SecurePass123!"],
    )
    role: str = Field(
        default="tenant",
        pattern=r"^(tenant|owner|provider|admin)$",
        description="Initial role",
    )


class LoginRequest(BaseModel):
    """Email + password login."""
    email: EmailStr
    password: str


class SendOTPRequest(BaseModel):
    """Request OTP for phone-based login."""
    phone: str = Field(
        ...,
        pattern=r"^\+\d{10,15}$",
        examples=["+919876543210"],
    )


class VerifyOTPRequest(BaseModel):
    """Verify OTP to complete phone-based login."""
    phone: str = Field(..., pattern=r"^\+\d{10,15}$")
    otp: str = Field(..., min_length=6, max_length=6)


class RefreshTokenRequest(BaseModel):
    """Exchange a refresh token for a new access + refresh token pair."""
    refresh_token: str


# ── Responses ──

class TokenResponse(BaseModel):
    """Access + refresh token pair returned on successful auth."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Full auth response with tokens + user profile."""
    tokens: TokenResponse
    user: dict  # UserResponse (will be refined in user schemas)
    is_new: bool = False
