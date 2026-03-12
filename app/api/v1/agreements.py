"""
LuxeLife API — Agreement routes.

Handles property booking, agreement signing, and agreement listing.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_roles
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.agreement import BookPropertyRequest, SignAgreementRequest
from app.services.agreement_service import AgreementService

router = APIRouter(prefix="/agreements", tags=["Agreements"])


@router.post("/book", status_code=201)
async def book_property(
    body: BookPropertyRequest,
    user: User = Depends(require_roles("tenant")),
    db: AsyncSession = Depends(get_db),
):
    """
    Book a property as a tenant.

    Creates a rental agreement + security deposit payment,
    and returns a Razorpay order for the deposit.
    """
    result = await AgreementService.book_property(
        db,
        tenant=user,
        property_id=body.property_id,
        lease_duration_months=body.lease_duration_months,
    )
    return success_response(result)


@router.post("/{agreement_id}/verify-deposit")
async def verify_deposit(
    agreement_id: str,
    body: dict,
    user: User = Depends(require_roles("tenant")),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify the security deposit payment via Razorpay.

    On success, advances the agreement to AWAITING_SIGNATURE.
    """
    result = await AgreementService.verify_deposit_and_advance(
        db,
        agreement_id=agreement_id,
        razorpay_order_id=body["razorpay_order_id"],
        razorpay_payment_id=body["razorpay_payment_id"],
        razorpay_signature=body["razorpay_signature"],
        payment_id=body["payment_id"],
    )
    return success_response(result)


@router.post("/{agreement_id}/sign")
async def sign_agreement(
    agreement_id: str,
    body: SignAgreementRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sign the rental agreement.

    Both tenant and owner must sign. Once both have signed,
    the agreement becomes ACTIVE and the first rent payment is generated.
    """
    result = await AgreementService.sign_agreement(
        db, agreement_id, user, body.signature
    )
    return success_response(result)


@router.get("/{agreement_id}")
async def get_agreement(
    agreement_id: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agreement details by ID."""
    result = await AgreementService.get_by_id(db, agreement_id)
    return success_response(result)


@router.get("")
async def list_agreements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List agreements for the current user (filtered by role)."""
    result = await AgreementService.list_by_user(db, user)
    return success_response(result)


@router.post("/generate-rent")
async def generate_monthly_rent(
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate next month's rent payments for all active agreements.
    **Admin only.** Normally triggered by a scheduled task.
    """
    result = await AgreementService.generate_monthly_rent(db)
    return success_response(result)
