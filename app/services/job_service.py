"""
LuxeLife API — Job service.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import generate_cuid
from app.models.job import Job, JobStatus
from app.models.property import Property
from app.models.user import User
from app.schemas.job import job_to_response


SERVICE_CATEGORIES = [
    {"id": "plumbing", "name": "Plumbing", "icon": "🔧"},
    {"id": "electrical", "name": "Electrical", "icon": "⚡"},
    {"id": "carpentry", "name": "Carpentry", "icon": "🪚"},
    {"id": "painting", "name": "Painting", "icon": "🎨"},
    {"id": "cleaning", "name": "Deep Cleaning", "icon": "🧹"},
    {"id": "pest_control", "name": "Pest Control", "icon": "🐛"},
    {"id": "appliance", "name": "Appliance Repair", "icon": "🔌"},
    {"id": "hvac", "name": "AC / HVAC", "icon": "❄️"},
    {"id": "general", "name": "General Maintenance", "icon": "🏠"},
]


class JobService:

    @staticmethod
    async def create(db: AsyncSession, user: User, **data) -> dict:
        prop = await db.get(Property, data["property_id"])
        if not prop:
            raise NotFoundError("Property")

        job = Job(
            id=generate_cuid(),
            service_type=data["service_type"],
            category=data["category"],
            description=data["description"],
            icon=next((c["icon"] for c in SERVICE_CATEGORIES if c["id"] == data["category"]), "🔧"),
            address=prop.address,
            tenant_name=user.name if user.active_role.value == "tenant" else None,
            status=JobStatus.SCHEDULED,
            scheduled_date=data.get("scheduled_date"),
            scheduled_time=data.get("scheduled_time"),
            property_id=data["property_id"],
            tenant_id=user.id if user.active_role.value == "tenant" else None,
        )
        db.add(job)
        await db.flush()
        return job_to_response(job)

    @staticmethod
    async def get_by_id(db: AsyncSession, job_id: str) -> dict:
        job = await db.get(Job, job_id)
        if not job:
            raise NotFoundError("Job")
        return job_to_response(job)

    @staticmethod
    async def update_status(db: AsyncSession, job_id: str, user: User, *, status: str | None = None, actual_cost: int | None = None) -> dict:
        job = await db.get(Job, job_id)
        if not job:
            raise NotFoundError("Job")
        if status:
            job.status = JobStatus(status)
            if status == "completed":
                job.completed_at = datetime.now(timezone.utc)
        if actual_cost is not None:
            job.actual_cost = actual_cost
        await db.flush()
        return job_to_response(job)

    @staticmethod
    async def assign_provider(db: AsyncSession, job_id: str, provider_id: str) -> dict:
        job = await db.get(Job, job_id)
        if not job:
            raise NotFoundError("Job")
        provider = await db.get(User, provider_id)
        if not provider:
            raise NotFoundError("Provider")
        job.provider_id = provider_id
        job.provider_name = provider.name
        job.status = JobStatus.ACTIVE
        await db.flush()
        return job_to_response(job)

    @staticmethod
    async def submit_work_report(db: AsyncSession, job_id: str, user: User, *, notes: str, materials_used: list, actual_cost: int, photos: list) -> dict:
        job = await db.get(Job, job_id)
        if not job:
            raise NotFoundError("Job")
        if job.provider_id != user.id:
            raise ForbiddenError("Only the assigned provider can submit reports")
        job.work_report = {"notes": notes, "materials_used": materials_used, "photos": photos}
        job.actual_cost = actual_cost
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return job_to_response(job)

    @staticmethod
    async def list_jobs(db: AsyncSession, user: User, *, page: int = 1, limit: int = 20, status: str | None = None, category: str | None = None, property_id: str | None = None, sort: str = "-created_at") -> tuple[list[dict], int]:
        query = select(Job)
        role = user.active_role.value
        if role == "tenant":
            query = query.where(Job.tenant_id == user.id)
        elif role == "provider":
            query = query.where(Job.provider_id == user.id)
        if status:
            query = query.where(Job.status == JobStatus(status))
        if category:
            query = query.where(Job.category == category)
        if property_id:
            query = query.where(Job.property_id == property_id)

        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0

        if sort.startswith("-"):
            col = getattr(Job, sort[1:], Job.created_at)
            query = query.order_by(col.desc())
        else:
            col = getattr(Job, sort, Job.created_at)
            query = query.order_by(col.asc())

        query = query.offset((page - 1) * limit).limit(limit)
        result = await db.execute(query)
        return [job_to_response(j) for j in result.scalars().all()], total

    @staticmethod
    def get_categories() -> list[dict]:
        return SERVICE_CATEGORIES
