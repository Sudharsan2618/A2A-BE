"""
LuxeLife API — Dispute routes.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.permissions import require_roles
from app.core.responses import paginated_response, success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import generate_cuid
from app.models.supporting import Dispute
from app.models.user import User

router = APIRouter(prefix="/disputes", tags=["Disputes"])


class DisputeCreate(BaseModel):
    job_id: str
    reason: str = Field(..., max_length=1000)


class DisputeUpdate(BaseModel):
    status: str | None = Field(None, pattern=r"^(open|in_review|resolved|escalated)$")
    resolution: str | None = Field(None, max_length=1000)


class SettlementProposal(BaseModel):
    amount: int = Field(..., ge=0)
    notes: str = ""


def _to_dict(d: Dispute) -> dict:
    return {
        "id": d.id, "job_id": d.job_id, "raised_by": d.raised_by,
        "reason": d.reason, "status": d.status, "resolution": d.resolution,
        "resolved_at": str(d.resolved_at) if d.resolved_at else None,
        "created_at": str(d.created_at),
    }


@router.get("")
async def list_disputes(
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    query = select(Dispute)
    if user.active_role.value != "admin":
        query = query.where(Dispute.raised_by == user.id)
    if status:
        query = query.where(Dispute.status == status)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.order_by(Dispute.created_at.desc()).offset((page - 1) * limit).limit(limit))
    return paginated_response([_to_dict(d) for d in result.scalars().all()], total, page, limit)


@router.post("", status_code=201)
async def create_dispute(body: DisputeCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    dispute = Dispute(id=generate_cuid(), job_id=body.job_id, raised_by=user.id, reason=body.reason)
    db.add(dispute)
    await db.flush()
    return success_response(_to_dict(dispute))


@router.get("/{dispute_id}")
async def get_dispute(dispute_id: str, _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    d = await db.get(Dispute, dispute_id)
    if not d:
        raise NotFoundError("Dispute")
    return success_response(_to_dict(d))


@router.patch("/{dispute_id}")
async def update_dispute(
    dispute_id: str, body: DisputeUpdate,
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    d = await db.get(Dispute, dispute_id)
    if not d:
        raise NotFoundError("Dispute")
    if body.status:
        d.status = body.status
        if body.status == "resolved":
            d.resolved_at = datetime.now(timezone.utc)
    if body.resolution:
        d.resolution = body.resolution
    await db.flush()
    return success_response(_to_dict(d))


@router.post("/{dispute_id}/settlement")
async def propose_settlement(
    dispute_id: str, body: SettlementProposal,
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    d = await db.get(Dispute, dispute_id)
    if not d:
        raise NotFoundError("Dispute")
    d.resolution = f"Settlement: ₹{body.amount / 100:.2f} — {body.notes}"
    d.status = "resolved"
    d.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    return success_response(_to_dict(d))
