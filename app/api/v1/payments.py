"""
LuxeLife API — Payment routes.

Handles payment listing, Razorpay initiation/verification, and earnings.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_roles
from app.core.responses import paginated_response, success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.payment import PaymentCreate, RentInitiateRequest, RentVerifyRequest
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── Listing ──

@router.get("")
async def list_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    type: str | None = Query(None),
    property_id: str | None = Query(None),
    sort: str = Query("-created_at"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List payments, filtered by the user's active role.

    - Tenant: sees their own payments.
    - Owner: sees payments for their properties.
    - Admin: sees all.
    """
    items, total = await PaymentService.list_payments(
        db,
        user,
        page=page,
        limit=limit,
        status=status,
        type=type,
        property_id=property_id,
        sort=sort,
    )
    return paginated_response(items, total, page, limit)


@router.get("/earnings")
async def get_owner_earnings(
    user: User = Depends(require_roles("owner")),
    db: AsyncSession = Depends(get_db),
):
    """Get owner earnings summary (revenue, commission, TDS, net payout)."""
    result = await PaymentService.get_owner_earnings(db, user.id)
    return success_response(result)


# ── Payment Detail ──

@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment details by ID."""
    from app.schemas.payment import payment_to_response
    payment = await PaymentService.get_by_id(db, payment_id)
    return success_response(payment_to_response(payment))


# ── Razorpay Flow ──

@router.post("/rent/initiate")
async def initiate_rent(
    body: RentInitiateRequest,
    user: User = Depends(require_roles("tenant")),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate a rent payment via Razorpay.

    Returns order details for the mobile app's Razorpay SDK.
    """
    result = await PaymentService.initiate_rent(db, body.payment_id, user)
    return success_response(result)


@router.post("/rent/verify")
async def verify_rent(
    body: RentVerifyRequest,
    user: User = Depends(require_roles("tenant")),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a Razorpay payment callback.

    Marks the payment as PAID or FAILED based on signature verification.
    """
    result = await PaymentService.verify_rent(
        db,
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        razorpay_signature=body.razorpay_signature,
        payment_id=body.payment_id,
    )
    return success_response(result)


# ── Admin ──

@router.post("", status_code=201)
async def create_payment(
    body: PaymentCreate,
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a payment record. **Admin only.**"""
    result = await PaymentService.create(db, **body.model_dump())
    return success_response(result)
