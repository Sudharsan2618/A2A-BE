"""
LuxeLife API — Inspection service.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import generate_cuid
from app.models.inspection import Inspection, InspectionStatus, InspectionType
from app.models.user import User
from app.schemas.inspection import inspection_to_response


class InspectionService:

    @staticmethod
    async def create(db: AsyncSession, user: User, **data) -> dict:
        insp = Inspection(
            id=generate_cuid(),
            type=InspectionType(data["type"]),
            status=InspectionStatus.SCHEDULED,
            scheduled_date=data["scheduled_date"],
            tenant_name=data["tenant_name"],
            inspector_id=user.id,
            property_id=data["property_id"],
            tenant_id=data["tenant_id"],
        )
        db.add(insp)
        await db.flush()
        return inspection_to_response(insp)

    @staticmethod
    async def get_by_id(db: AsyncSession, inspection_id: str) -> dict:
        insp = await db.get(Inspection, inspection_id)
        if not insp:
            raise NotFoundError("Inspection")
        return inspection_to_response(insp)

    @staticmethod
    async def update(db: AsyncSession, inspection_id: str, *, rooms=None, score=None, status=None) -> dict:
        insp = await db.get(Inspection, inspection_id)
        if not insp:
            raise NotFoundError("Inspection")
        if rooms is not None:
            insp.rooms = [r.model_dump() for r in rooms]
        if score is not None:
            insp.score = score
        if status:
            insp.status = InspectionStatus(status)
        await db.flush()
        return inspection_to_response(insp)

    @staticmethod
    async def complete(db: AsyncSession, inspection_id: str, *, summary: dict) -> dict:
        insp = await db.get(Inspection, inspection_id)
        if not insp:
            raise NotFoundError("Inspection")
        insp.status = InspectionStatus.COMPLETED
        insp.completed_date = datetime.now(timezone.utc)
        insp.summary = summary
        await db.flush()
        return inspection_to_response(insp)

    @staticmethod
    async def add_settlement(db: AsyncSession, inspection_id: str, *, settlement: dict) -> dict:
        insp = await db.get(Inspection, inspection_id)
        if not insp:
            raise NotFoundError("Inspection")
        insp.settlement = settlement
        await db.flush()
        return inspection_to_response(insp)

    @staticmethod
    async def list_inspections(db: AsyncSession, user: User, *, page: int = 1, limit: int = 20, status: str | None = None, property_id: str | None = None) -> tuple[list[dict], int]:
        query = select(Inspection)
        role = user.active_role.value
        if role == "tenant":
            query = query.where(Inspection.tenant_id == user.id)

        if status:
            query = query.where(Inspection.status == InspectionStatus(status))
        if property_id:
            query = query.where(Inspection.property_id == property_id)

        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
        query = query.order_by(Inspection.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await db.execute(query)
        return [inspection_to_response(i) for i in result.scalars().all()], total

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        total = (await db.execute(select(func.count(Inspection.id)))).scalar() or 0
        completed = (await db.execute(
            select(func.count(Inspection.id)).where(Inspection.status == InspectionStatus.COMPLETED)
        )).scalar() or 0
        avg_score = (await db.execute(
            select(func.avg(Inspection.score)).where(Inspection.score.isnot(None))
        )).scalar()
        return {"total": total, "completed": completed, "avg_score": round(avg_score or 0, 1)}
