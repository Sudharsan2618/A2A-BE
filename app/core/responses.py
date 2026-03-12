"""
LuxeLife API — Standard response wrapper.

Every API response uses this format:
  Success: { "success": true,  "data": {...}, "meta": {...} }
  Error:   { "success": false, "error": {"code": "...", "message": "..."} }
"""

from typing import Any

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""
    page: int
    limit: int
    total: int
    has_more: bool


class APIResponse(BaseModel):
    """Standard wrapper for all API responses."""
    success: bool = True
    data: Any = None
    meta: PaginationMeta | None = None


def success_response(
    data: Any = None,
    meta: PaginationMeta | None = None,
) -> dict:
    """Build a success response dict."""
    resp: dict[str, Any] = {"success": True, "data": data}
    if meta:
        resp["meta"] = meta.model_dump()
    return resp


def paginated_response(
    items: list[Any],
    total: int,
    page: int,
    limit: int,
) -> dict:
    """Build a paginated success response."""
    return success_response(
        data=items,
        meta=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            has_more=(page * limit) < total,
        ),
    )
