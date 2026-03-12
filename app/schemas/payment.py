"""
LuxeLife API — Payment schemas.

Request/response models for payment endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Requests ──

class PaymentCreate(BaseModel):
    """Create a new payment record (admin/system use)."""

    type: str = Field(..., pattern=r"^(rent|service|security_deposit)$")
    label: str = Field(..., max_length=200)
    amount: int = Field(..., gt=0, description="Amount in INR")
    breakdown: dict = Field(default={})
    due_date: datetime | None = None
    property_id: str
    tenant_id: str
    owner_id: str
    provider_id: str | None = None


class RentInitiateRequest(BaseModel):
    """Initiate a Razorpay payment for a pending payment."""

    payment_id: str


class RentVerifyRequest(BaseModel):
    """Verify a Razorpay payment callback."""

    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    payment_id: str


# ── Responses ──

class PaymentResponse(BaseModel):
    """Payment detail returned by API."""

    id: str
    type: str
    label: str
    amount: int
    breakdown: dict = {}
    status: str
    due_date: datetime | None = None
    paid_date: datetime | None = None
    method: str | None = None
    reference_id: str | None = None
    razorpay_order_id: str | None = None
    property_id: str
    tenant_id: str
    owner_id: str
    provider_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RentInitiateResponse(BaseModel):
    """Returned when a Razorpay order is created."""

    razorpay_order_id: str
    razorpay_key_id: str
    amount: int
    currency: str = "INR"
    payment_id: str


class EarningsSummary(BaseModel):
    """Owner earnings summary."""

    total_revenue: int
    commission: int
    commission_rate: float
    net_payout: int
    tds_deducted: int
    tds_rate: float
    monthly_trend: list[dict] = []


def payment_to_response(payment) -> dict:
    """Convert a Payment ORM object to a response dict."""
    return PaymentResponse(
        id=payment.id,
        type=payment.type.value,
        label=payment.label,
        amount=payment.amount,
        breakdown=payment.breakdown or {},
        status=payment.status.value,
        due_date=payment.due_date,
        paid_date=payment.paid_date,
        method=payment.method.value if payment.method else None,
        reference_id=payment.reference_id,
        razorpay_order_id=payment.razorpay_order_id,
        property_id=payment.property_id,
        tenant_id=payment.tenant_id,
        owner_id=payment.owner_id,
        provider_id=payment.provider_id,
        created_at=payment.created_at,
    ).model_dump()
