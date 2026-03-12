"""
LuxeLife API — Request logging middleware.

Logs every request with:
- Method, path, status code, duration
- Request ID (for tracing)
- User ID (if authenticated)

Uses structlog for structured JSON output in production.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every HTTP request with timing and tracing info."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get(
            "X-Request-ID", uuid.uuid4().hex[:12]
        )

        # Bind request context for structured logging
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.error("Unhandled exception in request")
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.info(
                "Request completed",
                status_code=response.status_code if "response" in dir() else 500,
                duration_ms=duration_ms,
            )

            structlog.contextvars.unbind_contextvars(
                "request_id", "method", "path"
            )

        # Add request ID to response headers (for client-side debugging)
        response.headers["X-Request-ID"] = request_id

        return response
