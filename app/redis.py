"""
LuxeLife API — Async Redis client.

Used for:
- OTP storage with TTL
- Rate limiting counters
- JWT token blacklisting (logout)
- Future: Celery broker, pub/sub
"""

from redis.asyncio import Redis, from_url

from app.config import settings

redis_client: Redis = from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


async def get_redis() -> Redis:
    """FastAPI dependency that returns the shared Redis client."""
    return redis_client
