"""
LuxeLife API — Job routes.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_roles
from app.core.responses import paginated_response, success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.job import JobAssign, JobCreate, JobUpdate, WorkReportSubmit
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/categories")
async def get_categories(_user: User = Depends(get_current_user)):
    """Get all service categories."""
    return success_response(JobService.get_categories())


@router.get("")
async def list_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    category: str | None = Query(None),
    property_id: str | None = Query(None),
    sort: str = Query("-created_at"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List jobs (role-filtered, paginated)."""
    items, total = await JobService.list_jobs(
        db, user, page=page, limit=limit, status=status,
        category=category, property_id=property_id, sort=sort,
    )
    return paginated_response(items, total, page, limit)


@router.get("/{job_id}")
async def get_job(job_id: str, _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get job detail."""
    return success_response(await JobService.get_by_id(db, job_id))


@router.post("", status_code=201)
async def create_job(
    body: JobCreate,
    user: User = Depends(require_roles("tenant", "owner")),
    db: AsyncSession = Depends(get_db),
):
    """Create a service request. **Tenant/Owner only.**"""
    return success_response(await JobService.create(db, user, **body.model_dump()))


@router.patch("/{job_id}")
async def update_job(
    job_id: str, body: JobUpdate,
    user: User = Depends(require_roles("provider", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update job status. **Provider/Admin only.**"""
    return success_response(await JobService.update_status(
        db, job_id, user, status=body.status, actual_cost=body.actual_cost,
    ))


@router.patch("/{job_id}/assign")
async def assign_provider(
    job_id: str, body: JobAssign,
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Assign a provider to a job. **Admin only.**"""
    return success_response(await JobService.assign_provider(db, job_id, body.provider_id))


@router.post("/{job_id}/work-report")
async def submit_work_report(
    job_id: str, body: WorkReportSubmit,
    user: User = Depends(require_roles("provider")),
    db: AsyncSession = Depends(get_db),
):
    """Submit work completion report. **Provider only.**"""
    return success_response(await JobService.submit_work_report(
        db, job_id, user, notes=body.notes, materials_used=body.materials_used,
        actual_cost=body.actual_cost, photos=body.photos,
    ))
