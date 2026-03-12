"""
LuxeLife API — Agreement service.

Business logic for booking properties, creating agreements,
signing, and generating first rent payment records.
"""

from datetime import datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models import generate_cuid
from app.models.agreement import Agreement, AgreementStatus
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.property import Occupancy, Property
from app.models.user import User
from app.schemas.agreement import agreement_to_response
from app.services.razorpay_service import RazorpayService
from app.config import settings


AGREEMENT_TEMPLATE = """RESIDENTIAL LEASE AGREEMENT

This Residential Lease Agreement ("Agreement") is entered into as of {start_date},
by and between:

LANDLORD: {owner_name}
(hereinafter referred to as "Owner")

TENANT: {tenant_name}
(hereinafter referred to as "Tenant")

PROPERTY: {property_name}, {property_unit}
ADDRESS: {property_address}, {property_city}, {property_state} - {property_pincode}

TERMS AND CONDITIONS:

1. LEASE TERM: This lease shall commence on {start_date} and shall continue for
   a period of {lease_months} months, ending on {end_date}, unless terminated
   earlier in accordance with the terms of this Agreement.

2. MONTHLY RENT: The Tenant agrees to pay a monthly rent of INR {rent_amount}
   (Rupees {rent_words} only), payable on or before the 5th day of each calendar month.

3. SECURITY DEPOSIT: The Tenant has paid a security deposit of INR {deposit_amount}
   (Rupees {deposit_words} only), which shall be refunded at the end of the lease
   term, subject to deductions for damages or unpaid dues.

4. MAINTENANCE CHARGES: The Tenant shall pay monthly maintenance charges of
   INR {maintenance_amount} in addition to the rent.

5. USE OF PREMISES: The premises shall be used exclusively for residential purposes.

6. TERMINATION: Either party may terminate this agreement by providing 2 months
   written notice to the other party.

7. GOVERNING LAW: This Agreement shall be governed by the laws of India and the
   State of {property_state}.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first
written above.
"""


def _amount_to_words(amount: int) -> str:
    """Simple converter for common rent ranges."""
    if amount == 0:
        return "Zero"
    # Basic implementation for display
    return f"{amount:,}"


class AgreementService:
    """Handles agreement and booking operations."""

    @staticmethod
    async def book_property(
        db: AsyncSession, tenant: User, property_id: str, lease_duration_months: int = 12
    ) -> dict:
        """
        Full booking flow:
        1. Verify property is vacant
        2. Create agreement record
        3. Create security deposit payment record
        4. Create Razorpay order for the deposit
        5. Return agreement + payment info for frontend
        """
        # Load property with owner
        result = await db.execute(
            select(Property)
            .options(selectinload(Property.owner))
            .where(Property.id == property_id)
        )
        prop = result.scalar_one_or_none()
        if not prop:
            raise NotFoundError("Property")

        if prop.occupancy == Occupancy.OCCUPIED:
            raise BadRequestError("This property is currently occupied")

        if prop.owner_id == tenant.id:
            raise BadRequestError("You cannot book your own property")

        # Check for existing active/pending agreement
        existing = await db.execute(
            select(Agreement)
            .options(
                selectinload(Agreement.property),
                selectinload(Agreement.tenant),
                selectinload(Agreement.owner),
            )
            .where(
                Agreement.property_id == property_id,
                Agreement.tenant_id == tenant.id,
                Agreement.status.in_([
                    AgreementStatus.DRAFT,
                    AgreementStatus.AWAITING_PAYMENT,
                    AgreementStatus.AWAITING_SIGNATURE,
                    AgreementStatus.ACTIVE,
                ]),
            )
        )
        existing_agr = existing.scalar_one_or_none()

        if existing_agr:
            # If already signed / active — block
            if existing_agr.status in (AgreementStatus.AWAITING_SIGNATURE, AgreementStatus.ACTIVE):
                raise BadRequestError("You already have an active or pending booking for this property")

            # Reuse awaiting_payment / draft: create a fresh Razorpay order for the deposit
            dep_result = await db.execute(
                select(Payment).where(Payment.id == existing_agr.deposit_payment_id)
            )
            dep = dep_result.scalar_one_or_none()
            if dep and dep.status == PaymentStatus.PENDING:
                order = RazorpayService.create_order(
                    amount=dep.amount,
                    notes={
                        "payment_id": dep.id,
                        "agreement_id": existing_agr.id,
                        "tenant_id": tenant.id,
                        "property_id": prop.id,
                        "type": "security_deposit",
                    },
                )
                dep.razorpay_order_id = order["id"]
                await db.flush()
                await db.refresh(existing_agr)
                return {
                    "agreement": agreement_to_response(existing_agr),
                    "payment": {
                        "payment_id": dep.id,
                        "razorpay_order_id": order["id"],
                        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                        "amount": dep.amount,
                        "currency": "INR",
                        "description": f"Security Deposit — {prop.name}",
                    },
                }
            # Deposit already paid/failed — block
            raise BadRequestError("You already have a pending booking for this property")

        now = datetime.now(timezone.utc)
        lease_start = now + timedelta(days=7)  # move-in 7 days from now
        lease_end = lease_start + relativedelta(months=lease_duration_months)

        owner = prop.owner

        # Generate agreement text
        terms = AGREEMENT_TEMPLATE.format(
            start_date=lease_start.strftime("%B %d, %Y"),
            end_date=lease_end.strftime("%B %d, %Y"),
            owner_name=owner.name if owner else "Property Owner",
            tenant_name=tenant.name,
            property_name=prop.name,
            property_unit=prop.unit,
            property_address=prop.address,
            property_city=prop.city,
            property_state=prop.state,
            property_pincode=prop.pincode,
            lease_months=lease_duration_months,
            rent_amount=f"{prop.rent:,}",
            rent_words=_amount_to_words(prop.rent),
            deposit_amount=f"{prop.security_deposit:,}",
            deposit_words=_amount_to_words(prop.security_deposit),
            maintenance_amount=f"{prop.maintenance_charges:,}",
        )

        # Create deposit payment record
        deposit_payment = Payment(
            id=generate_cuid(),
            type=PaymentType.SECURITY_DEPOSIT,
            label=f"Security Deposit — {prop.name}, {prop.unit}",
            amount=prop.security_deposit,
            breakdown={"security_deposit": prop.security_deposit},
            status=PaymentStatus.PENDING,
            due_date=now + timedelta(days=3),
            property_id=prop.id,
            tenant_id=tenant.id,
            owner_id=prop.owner_id,
        )
        db.add(deposit_payment)
        await db.flush()

        # Create agreement
        agreement = Agreement(
            id=generate_cuid(),
            status=AgreementStatus.AWAITING_PAYMENT,
            rent_amount=prop.rent,
            security_deposit=prop.security_deposit,
            maintenance_charges=prop.maintenance_charges,
            lease_start=lease_start,
            lease_end=lease_end,
            lease_duration_months=lease_duration_months,
            terms_text=terms,
            property_id=prop.id,
            tenant_id=tenant.id,
            owner_id=prop.owner_id,
            deposit_payment_id=deposit_payment.id,
        )
        db.add(agreement)
        await db.flush()

        # Create Razorpay order for deposit
        order = RazorpayService.create_order(
            amount=prop.security_deposit,
            notes={
                "payment_id": deposit_payment.id,
                "agreement_id": agreement.id,
                "tenant_id": tenant.id,
                "property_id": prop.id,
                "type": "security_deposit",
            },
        )
        deposit_payment.razorpay_order_id = order["id"]
        await db.flush()
        await db.refresh(agreement)

        return {
            "agreement": agreement_to_response(agreement, prop=prop, tenant=tenant, owner=owner),
            "payment": {
                "payment_id": deposit_payment.id,
                "razorpay_order_id": order["id"],
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "amount": prop.security_deposit,
                "currency": "INR",
                "description": f"Security Deposit — {prop.name}",
            },
        }

    @staticmethod
    async def verify_deposit_and_advance(
        db: AsyncSession,
        *,
        agreement_id: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        payment_id: str,
    ) -> dict:
        """
        Verify the deposit payment via Razorpay, then advance the agreement
        to AWAITING_SIGNATURE status.
        """
        # Load agreement
        result = await db.execute(
            select(Agreement)
            .options(
                selectinload(Agreement.property),
                selectinload(Agreement.tenant),
                selectinload(Agreement.owner),
            )
            .where(Agreement.id == agreement_id)
        )
        agreement = result.scalar_one_or_none()
        if not agreement:
            raise NotFoundError("Agreement")

        if agreement.status != AgreementStatus.AWAITING_PAYMENT:
            raise BadRequestError(f"Agreement is in {agreement.status.value} state, cannot verify payment")

        # Load payment
        pay_result = await db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = pay_result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment")

        if payment.razorpay_order_id != razorpay_order_id:
            raise BadRequestError("Order ID mismatch")

        # Verify signature
        is_valid = RazorpayService.verify_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
        )

        if is_valid:
            payment.status = PaymentStatus.PAID
            payment.paid_date = datetime.now(timezone.utc)
            payment.reference_id = razorpay_payment_id
            agreement.status = AgreementStatus.AWAITING_SIGNATURE
        else:
            payment.status = PaymentStatus.FAILED
            raise BadRequestError("Payment verification failed")

        await db.flush()
        await db.refresh(agreement)
        return agreement_to_response(agreement)

    @staticmethod
    async def sign_agreement(
        db: AsyncSession, agreement_id: str, user: User, signature: str
    ) -> dict:
        """
        Record a signature on the agreement.
        If both parties have signed, activate the agreement and generate first rent.
        """
        result = await db.execute(
            select(Agreement)
            .options(
                selectinload(Agreement.property),
                selectinload(Agreement.tenant),
                selectinload(Agreement.owner),
            )
            .where(Agreement.id == agreement_id)
        )
        agreement = result.scalar_one_or_none()
        if not agreement:
            raise NotFoundError("Agreement")

        if agreement.status not in (
            AgreementStatus.AWAITING_SIGNATURE, AgreementStatus.SIGNED
        ):
            raise BadRequestError(f"Agreement cannot be signed in {agreement.status.value} state")

        now = datetime.now(timezone.utc)

        if user.id == agreement.tenant_id:
            agreement.tenant_signature = signature
            agreement.tenant_signed_at = now
        elif user.id == agreement.owner_id:
            agreement.owner_signature = signature
            agreement.owner_signed_at = now
        else:
            raise ForbiddenError("You are not a party to this agreement")

        # Check if both signed
        if agreement.tenant_signature and agreement.owner_signature:
            agreement.status = AgreementStatus.ACTIVE

            # Update property: mark occupied + assign tenant
            prop = agreement.property
            prop.occupancy = Occupancy.OCCUPIED
            prop.tenant_id = agreement.tenant_id
            prop.lease_start = agreement.lease_start
            prop.lease_end = agreement.lease_end

            # Generate first month's rent payment
            await AgreementService._generate_rent_payment(db, agreement)
        else:
            agreement.status = AgreementStatus.SIGNED

        await db.flush()
        await db.refresh(agreement)
        return agreement_to_response(agreement)

    @staticmethod
    async def _generate_rent_payment(db: AsyncSession, agreement: Agreement):
        """Create the first month's rent payment record after agreement activation."""
        lease_start = agreement.lease_start or datetime.now(timezone.utc)
        # Due on the 5th of the lease start month
        due_date = lease_start.replace(day=5)
        if due_date < datetime.now(timezone.utc):
            due_date = due_date + relativedelta(months=1)

        prop = agreement.property
        rent_payment = Payment(
            id=generate_cuid(),
            type=PaymentType.RENT,
            label=f"Monthly Rent — {prop.name}, {prop.unit}",
            amount=agreement.rent_amount,
            breakdown={
                "rent": agreement.rent_amount,
                "maintenance": agreement.maintenance_charges,
            },
            status=PaymentStatus.PENDING,
            due_date=due_date,
            property_id=agreement.property_id,
            tenant_id=agreement.tenant_id,
            owner_id=agreement.owner_id,
        )
        db.add(rent_payment)

    @staticmethod
    async def get_by_id(db: AsyncSession, agreement_id: str) -> dict:
        """Get agreement detail."""
        result = await db.execute(
            select(Agreement)
            .options(
                selectinload(Agreement.property),
                selectinload(Agreement.tenant),
                selectinload(Agreement.owner),
            )
            .where(Agreement.id == agreement_id)
        )
        agreement = result.scalar_one_or_none()
        if not agreement:
            raise NotFoundError("Agreement")
        return agreement_to_response(agreement)

    @staticmethod
    async def list_by_user(db: AsyncSession, user: User) -> list[dict]:
        """List agreements for the current user based on role."""
        query = select(Agreement).options(
            selectinload(Agreement.property),
            selectinload(Agreement.tenant),
            selectinload(Agreement.owner),
        )

        role = user.active_role.value
        if role == "tenant":
            query = query.where(Agreement.tenant_id == user.id)
        elif role == "owner":
            query = query.where(Agreement.owner_id == user.id)
        # admin sees all

        query = query.order_by(Agreement.created_at.desc())
        result = await db.execute(query)
        return [agreement_to_response(a) for a in result.scalars().all()]

    @staticmethod
    async def generate_monthly_rent(db: AsyncSession):
        """
        Generate next month's rent payments for all active agreements.
        Called by a scheduled task or admin action.
        """
        now = datetime.now(timezone.utc)
        next_month = now + relativedelta(months=1)
        due_date = next_month.replace(day=5)

        # Find active agreements
        result = await db.execute(
            select(Agreement)
            .options(selectinload(Agreement.property))
            .where(Agreement.status == AgreementStatus.ACTIVE)
        )
        agreements = result.scalars().all()

        created = 0
        for agr in agreements:
            # Check if a rent payment already exists for this month
            existing = await db.execute(
                select(Payment).where(
                    Payment.property_id == agr.property_id,
                    Payment.tenant_id == agr.tenant_id,
                    Payment.type == PaymentType.RENT,
                    Payment.due_date >= now.replace(day=1),
                    Payment.due_date < (now.replace(day=1) + relativedelta(months=1)),
                )
            )
            if existing.scalar_one_or_none():
                continue

            prop = agr.property
            payment = Payment(
                id=generate_cuid(),
                type=PaymentType.RENT,
                label=f"Monthly Rent — {prop.name}, {prop.unit}",
                amount=agr.rent_amount,
                breakdown={
                    "rent": agr.rent_amount,
                    "maintenance": agr.maintenance_charges,
                },
                status=PaymentStatus.PENDING,
                due_date=due_date,
                property_id=agr.property_id,
                tenant_id=agr.tenant_id,
                owner_id=agr.owner_id,
            )
            db.add(payment)
            created += 1

        await db.flush()
        return {"created": created, "total_active": len(agreements)}
