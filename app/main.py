"""
LuxeLife API — Application factory.

Creates and configures the FastAPI application with:
- CORS middleware
- Rate limiting
- Request logging
- Global exception handlers
- API route mounting
- Startup/shutdown lifecycle hooks
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.database import engine
from app.redis import redis_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.

    - Startup: verify DB and Redis connections.
    - Shutdown: dispose engine and close Redis pool gracefully.
    """
    # ── Startup ──
    logger.info("Starting LuxeLife API", debug=settings.DEBUG)

    # Verify database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        logger.info("Database connection verified")
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        raise

    # Verify Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.warning("Redis connection failed — OTP and rate limiting disabled", error=str(e))

    yield

    # ── Shutdown ──
    logger.info("Shutting down LuxeLife API")
    await engine.dispose()
    await redis_client.aclose()
    logger.info("Connections closed cleanly")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ──

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # Request logging
    from app.middleware.request_logger import RequestLoggerMiddleware
    app.add_middleware(RequestLoggerMiddleware)

    # ── Exception Handlers ──
    register_exception_handlers(app)

    # ── Routes ──
    from app.api.health import router as health_router
    from app.api.v1.router import v1_router

    app.include_router(health_router)
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    # ── Sentry (if configured) ──
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            send_default_pii=False,
        )

    return app


# ── App instance (imported by uvicorn) ──
app = create_app()
