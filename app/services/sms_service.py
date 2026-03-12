"""
LuxeLife API — SMS service (Twilio).

Sends OTP and transactional SMS messages via Twilio.
Falls back to console logging in debug mode if Twilio is not configured.
"""

import structlog

from app.config import settings

logger = structlog.get_logger()


class SMSService:
    """Twilio SMS integration."""

    _client = None

    @classmethod
    def _get_client(cls):
        """Lazy-initialize the Twilio client."""
        if cls._client is None:
            if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
                return None
            from twilio.rest import Client
            cls._client = Client(
                settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
            )
        return cls._client

    @classmethod
    def send_otp(cls, phone: str, otp: str) -> None:
        """Send an OTP message to the given phone number."""
        message = (
            f"Your LuxeLife verification code is {otp}. "
            f"Valid for 5 minutes. Do not share this code."
        )
        cls._send(phone, message)

    @classmethod
    def _send(cls, phone: str, message: str) -> None:
        """Send an SMS message. Falls back to console in debug mode."""
        client = cls._get_client()

        if client is None:
            logger.warning(
                "Twilio not configured — printing SMS to console",
                phone=phone,
                message=message,
            )
            print(f"\n{'='*50}")
            print(f"  SMS to {phone}")
            print(f"  {message}")
            print(f"{'='*50}\n")
            return

        try:
            client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone,
            )
            logger.info("SMS sent", phone=phone)
        except Exception as e:
            logger.error("SMS send failed", phone=phone, error=str(e))
            if settings.DEBUG:
                print(f"\n[SMS FAILED] {phone}: {message}\n")
            else:
                raise
