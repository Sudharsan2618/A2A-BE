"""
LuxeLife API — Custom exception hierarchy.

All application errors extend AppException, which carries:
- HTTP status code
- Machine-readable error code
- Human-readable message
- Optional details (validation errors, etc.)

The global exception handler in main.py converts these to standard JSON responses.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found (404)."""

    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(404, "NOT_FOUND", f"{resource} not found")


class UnauthorizedError(AppException):
    """Authentication required or failed (401)."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(401, "UNAUTHORIZED", message)


class ForbiddenError(AppException):
    """Insufficient permissions (403)."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(403, "FORBIDDEN", message)


class ConflictError(AppException):
    """Duplicate or conflicting resource (409)."""

    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(409, "CONFLICT", message)


class BadRequestError(AppException):
    """Client sent invalid data (400)."""

    def __init__(
        self,
        message: str = "Bad request",
        details: list[Any] | None = None,
    ) -> None:
        super().__init__(400, "BAD_REQUEST", message, details)


class RateLimitedError(AppException):
    """Too many requests (429)."""

    def __init__(self, message: str = "Too many requests. Try again later.") -> None:
        super().__init__(429, "RATE_LIMITED", message)


# ── Global Exception Handler ──

def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(
        _request: Request, exc: AppException
    ) -> JSONResponse:
        body: dict[str, Any] = {
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        }
        if exc.details:
            body["error"]["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        # Log the full traceback in production via Sentry / structlog
        import traceback
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                },
            },
        )
