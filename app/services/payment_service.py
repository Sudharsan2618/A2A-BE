"""
LuxeLife API — Payment service.

Business logic for payment CRUD, Razorpay initiation, verification, and earnings.
"""

from datetime import datetime, timezone
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models import generate_cuid
from app.models.payment import Payment, PaymentMethod, PaymentStatus, PaymentType
from app.models.user import User
from app.schemas.payment import payment_to_response
from app.services.razorpay_service import RazorpayService


class PaymentService:
    """Handles payment operations."""

    @staticmethod
    async def create(db: AsyncSession, **data) -> dict:
        """Create a new payment record."""
        payment = Payment(
            id=generate_cuid(),
            type=PaymentType(data["type"]),
            label=data["label"],
            amount=data["amount"],
            breakdown=data.get("breakdown", {}),
            due_date=data.get("due_date"),
            property_id=data["property_id"],
            tenant_id=data["tenant_id"],
            owner_id=data["owner_id"],
            provider_id=data.get("provider_id"),
        )
        db.add(payment)
        await db.flush()
        return payment_to_response(payment)

    @staticmethod
    async def get_by_id(db: AsyncSession, payment_id: str) -> Payment:
        """Get a payment by ID. Returns the ORM object."""
        result = await db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment")
        return payment

    @staticmethod
    async def list_payments(
        db: AsyncSession,
        user: User,
        *,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        type: str | None = None,
        property_id: str | None = None,
        sort: str = "-created_at",
    ) -> tuple[list[dict], int]:
        """
        List payments, filtered by the user's role.

        - Tenant: sees their own payments.
        - Owner: sees payments for their properties.
        - Admin: sees all payments.
        """
        query = select(Payment)

        # Role-based filtering
        role = user.active_role.value
        if role == "tenant":
            query = query.where(Payment.tenant_id == user.id)
        elif role == "owner":
            query = query.where(Payment.owner_id == user.id)
        elif role == "provider":
            query = query.where(Payment.provider_id == user.id)
        # admin: no role filter

        # Additional filters
        if status:
            query = query.where(Payment.status == PaymentStatus(status))
        if type:
            query = query.where(Payment.type == PaymentType(type))
        if property_id:
            query = query.where(Payment.property_id == property_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # Sort
        if sort.startswith("-"):
            col = getattr(Payment, sort[1:], Payment.created_at)
            query = query.order_by(col.desc())
        else:
            col = getattr(Payment, sort, Payment.created_at)
            query = query.order_by(col.asc())

        # Paginate
        query = query.offset((page - 1) * limit).limit(limit)

        result = await db.execute(query)
        payments = result.scalars().all()

        return [payment_to_response(p) for p in payments], total

    @staticmethod
    async def initiate_rent(
        db: AsyncSession, payment_id: str, user: User
    ) -> dict:
        logger = logging.getLogger(__name__)
        logger.info("Initiating rent payment", payment_id=payment_id, user_id=user.id)
        payment = await PaymentService.get_by_id(db, payment_id)
        if not payment:
            logger.error("Payment not found", payment_id=payment_id)
            raise NotFoundError("Payment")
        if payment.tenant_id != user.id:
            logger.error("Payment does not belong to user", payment_id=payment_id, payment_tenant_id=payment.tenant_id, user_id=user.id)
            raise BadRequestError("This payment does not belong to you")
        if payment.status not in (PaymentStatus.PENDING, PaymentStatus.OVERDUE):
            logger.error("Payment not in payable status", payment_id=payment_id, status=payment.status.value)
            raise BadRequestError(f"Cannot pay a {payment.status.value} payment")
        
        logger.info("Creating Razorpay order for rent payment", amount=payment.amount)
        order = RazorpayService.create_order(
            amount=payment.amount,
            notes={
                "payment_id": payment.id,
                "tenant_id": user.id,
                "property_id": payment.property_id,
            },
        )
        logger.info("Razorpay order created", order_id=order.get("id"), is_mock=order.get("id", "").startswith("order_mock"))
        payment.razorpay_order_id = order["id"]
        await db.flush()
        return {
            "razorpay_order_id": order["id"],
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "amount": payment.amount,
            "currency": "INR",
            "payment_id": payment.id,
        }

    @staticmethod
    async def verify_rent(
        db: AsyncSession,
        *,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        payment_id: str,
    ) -> dict:
        """
        Verify a Razorpay payment callback.

        1. Verify the HMAC signature.
        2. If valid, mark payment as PAID.
        3. If invalid, mark as FAILED.
        """
        payment = await PaymentService.get_by_id(db, payment_id)

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
            # Detect payment method from Razorpay
            rz_payment = RazorpayService.fetch_payment(razorpay_payment_id)
            if rz_payment and rz_payment.get("method"):
                method_map = {
                    "upi": PaymentMethod.UPI,
                    "card": PaymentMethod.CARD,
                    "netbanking": PaymentMethod.NETBANKING,
                    "wallet": PaymentMethod.WALLET,
                }
                payment.method = method_map.get(rz_payment["method"])
        else:
            payment.status = PaymentStatus.FAILED

        await db.flush()
        return payment_to_response(payment)

    @staticmethod
    async def get_owner_earnings(
        db: AsyncSession, owner_id: str
    ) -> dict:
        """
        Calculate owner earnings summary.

        - Total revenue from paid rent payments.
        - 10% platform commission.
        - TDS deducted at 10% rate.
        """
        result = await db.execute(
            select(func.sum(Payment.amount)).where(
                Payment.owner_id == owner_id,
                Payment.type == PaymentType.RENT,
                Payment.status == PaymentStatus.PAID,
            )
        )
        total_revenue = result.scalar() or 0

        commission_rate = 0.10
        tds_rate = 0.10
        commission = int(total_revenue * commission_rate)
        tds = int(total_revenue * tds_rate)
        net_payout = total_revenue - commission - tds

        return {
            "total_revenue": total_revenue,
            "commission": commission,
            "commission_rate": commission_rate,
            "net_payout": net_payout,
            "tds_deducted": tds,
            "tds_rate": tds_rate,
            "monthly_trend": [],  # TODO: aggregate by month
        }
