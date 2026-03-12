"""
LuxeLife API — Inspection schemas.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class RoomItem(BaseModel):
    name: str
    condition: str = Field(..., pattern=r"^(good|fair|damaged)$")
    notes: str = ""
    photos: list[str] = []


class RoomInspection(BaseModel):
    name: str
    status: str = Field(..., pattern=r"^(good|flagged)$")
    items: list[RoomItem] = []


class InspectionCreate(BaseModel):
    type: str = Field(..., pattern=r"^(move_in|move_out|periodic)$")
    property_id: str
    tenant_id: str
    tenant_name: str
    scheduled_date: datetime


class InspectionUpdate(BaseModel):
    rooms: list[RoomInspection] | None = None
    score: float | None = Field(None, ge=0, le=100)
    status: str | None = Field(None, pattern=r"^(scheduled|in_progress|completed|disputed)$")


class InspectionComplete(BaseModel):
    summary: dict = {}


class SettlementProposal(BaseModel):
    deposit_amount: int = Field(..., ge=0)
    deductions: list[dict] = []
    refund_amount: int = Field(..., ge=0)
    notes: str = ""


class InspectionResponse(BaseModel):
    id: str
    type: str
    status: str
    scheduled_date: datetime
    completed_date: datetime | None = None
    score: float | None = None
    tenant_name: str
    inspector_id: str
    rooms: list = []
    summary: dict | None = None
    settlement: dict | None = None
    property_id: str
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


def inspection_to_response(insp) -> dict:
    return InspectionResponse(
        id=insp.id, type=insp.type.value, status=insp.status.value,
        scheduled_date=insp.scheduled_date, completed_date=insp.completed_date,
        score=insp.score, tenant_name=insp.tenant_name, inspector_id=insp.inspector_id,
        rooms=insp.rooms or [], summary=insp.summary, settlement=insp.settlement,
        property_id=insp.property_id, tenant_id=insp.tenant_id,
        created_at=insp.created_at,
    ).model_dump()
