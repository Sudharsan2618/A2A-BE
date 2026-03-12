"""
LuxeLife API — Inspection routes.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_roles
from app.core.responses import paginated_response, success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.inspection import InspectionComplete, InspectionCreate, InspectionUpdate, SettlementProposal
from app.services.inspection_service import InspectionService

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.get("")
async def list_inspections(
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None), property_id: str | None = Query(None),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items, total = await InspectionService.list_inspections(
        db, user, page=page, limit=limit, status=status, property_id=property_id,
    )
    return paginated_response(items, total, page, limit)


@router.get("/stats")
async def get_stats(_admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return success_response(await InspectionService.get_stats(db))


@router.get("/{inspection_id}")
async def get_inspection(inspection_id: str, _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return success_response(await InspectionService.get_by_id(db, inspection_id))


@router.post("", status_code=201)
async def create_inspection(
    body: InspectionCreate,
    user: User = Depends(require_roles("admin", "owner")),
    db: AsyncSession = Depends(get_db),
):
    return success_response(await InspectionService.create(db, user, **body.model_dump()))


@router.patch("/{inspection_id}")
async def update_inspection(
    inspection_id: str, body: InspectionUpdate,
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return success_response(await InspectionService.update(
        db, inspection_id, rooms=body.rooms, score=body.score, status=body.status,
    ))


@router.post("/{inspection_id}/complete")
async def complete_inspection(
    inspection_id: str, body: InspectionComplete,
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return success_response(await InspectionService.complete(db, inspection_id, summary=body.summary))


@router.post("/{inspection_id}/settlement")
async def add_settlement(
    inspection_id: str, body: SettlementProposal,
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return success_response(await InspectionService.add_settlement(db, inspection_id, settlement=body.model_dump()))
