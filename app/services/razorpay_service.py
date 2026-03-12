"""
LuxeLife API — Razorpay service.

Handles payment order creation and signature verification.
Uses the official Razorpay Python SDK.
"""

import hashlib
import hmac

import structlog

from app.config import settings

logger = structlog.get_logger()


class RazorpayService:
    """Razorpay payment gateway integration."""

    _client = None

    @classmethod
    def _get_client(cls):
        """Lazy-initialize the Razorpay client."""
        if cls._client is None:
            if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
                logger.warning("Razorpay credentials not configured")
                return None
            import razorpay
            cls._client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        return cls._client

    @classmethod
    def create_order(
        cls,
        amount: int,
        currency: str = "INR",
        notes: dict | None = None,
    ) -> dict:
        """
        Create a Razorpay order.

        Args:
            amount: Amount in INR (e.g. 35000 = ₹35,000).
            currency: Currency code (default INR).
            notes: Metadata to associate with the order.

        Returns:
            Razorpay order dict with id, amount, status, etc.
        """
        logger.info("Creating Razorpay order", amount=amount, currency=currency)
        logger.info("Razorpay config", key_id=settings.RAZORPAY_KEY_ID, has_secret=bool(settings.RAZORPAY_KEY_SECRET))
        
        client = cls._get_client()
        if client is None:
            # Return mock order for development
            logger.warning("Razorpay not configured — returning mock order")
            return {
                "id": f"order_mock_{amount}",
                "amount": amount,
                "currency": currency,
                "status": "created",
            }

        logger.info("Razorpay client obtained, creating order...")
        # Razorpay SDK expects paise, so multiply INR by 100
        order = client.order.create({
            "amount": amount * 100,
            "currency": currency,
            "notes": notes or {},
            "payment_capture": 1,  # auto-capture on success
        })
        logger.info("Razorpay order created", order_id=order["id"], amount=amount)
        return order

    @classmethod
    def verify_signature(
        cls,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """
        Verify a Razorpay payment callback signature.

        Uses HMAC-SHA256 to verify: order_id|payment_id against signature.
        """
        client = cls._get_client()
        if client is None:
            # Auto-verify in dev mode
            logger.warning("Razorpay not configured — auto-verifying")
            return True

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
            logger.info("Payment signature verified", order_id=order_id)
            return True
        except Exception as e:
            logger.error("Payment signature verification failed", error=str(e))
            return False

    @classmethod
    def fetch_payment(cls, payment_id: str) -> dict | None:
        """Fetch payment details from Razorpay."""
        client = cls._get_client()
        if client is None:
            return None
        try:
            return client.payment.fetch(payment_id)
        except Exception as e:
            logger.error("Failed to fetch payment", error=str(e))
            return None
