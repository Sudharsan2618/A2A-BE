"""
LuxeLife API — Job schemas.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    service_type: str = Field(..., max_length=100)
    category: str = Field(..., max_length=100)
    description: str = Field(..., max_length=2000)
    property_id: str
    scheduled_date: datetime | None = None
    scheduled_time: str | None = Field(None, max_length=20)


class JobUpdate(BaseModel):
    status: str | None = Field(None, pattern=r"^(scheduled|active|completed|disputed|cancelled)$")
    actual_cost: int | None = Field(None, gt=0)


class JobAssign(BaseModel):
    provider_id: str


class WorkReportSubmit(BaseModel):
    notes: str = Field(..., max_length=2000)
    materials_used: list[str] = []
    actual_cost: int = Field(..., gt=0)
    photos: list[str] = []


class JobResponse(BaseModel):
    id: str
    service_type: str
    category: str
    description: str
    icon: str
    address: str
    tenant_name: str | None = None
    provider_name: str | None = None
    status: str
    scheduled_date: datetime | None = None
    scheduled_time: str | None = None
    estimated_cost: dict = {}
    actual_cost: int | None = None
    completed_at: datetime | None = None
    work_report: dict | None = None
    property_id: str
    tenant_id: str | None = None
    provider_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


def job_to_response(job) -> dict:
    return JobResponse(
        id=job.id, service_type=job.service_type, category=job.category,
        description=job.description, icon=job.icon, address=job.address,
        tenant_name=job.tenant_name, provider_name=job.provider_name,
        status=job.status.value, scheduled_date=job.scheduled_date,
        scheduled_time=job.scheduled_time, estimated_cost=job.estimated_cost or {},
        actual_cost=job.actual_cost, completed_at=job.completed_at,
        work_report=job.work_report, property_id=job.property_id,
        tenant_id=job.tenant_id, provider_id=job.provider_id,
        created_at=job.created_at,
    ).model_dump()
