"""
LuxeLife API — Agreement schemas.

Request/response models for agreement/booking endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class BookPropertyRequest(BaseModel):
    """Tenant initiates booking a property — creates agreement + deposit payment."""
    property_id: str
    lease_duration_months: int = Field(default=12, ge=6, le=36)


class SignAgreementRequest(BaseModel):
    """Submit a signature for the agreement."""
    signature: str = Field(..., min_length=1, description="Base64 signature image or URL")


class AgreementResponse(BaseModel):
    """Agreement detail returned by API."""
    id: str
    status: str
    rent_amount: int
    security_deposit: int
    maintenance_charges: int
    lease_start: datetime | None = None
    lease_end: datetime | None = None
    lease_duration_months: int
    terms_text: str | None = None
    tenant_signature: str | None = None
    owner_signature: str | None = None
    tenant_signed_at: datetime | None = None
    owner_signed_at: datetime | None = None
    pdf_url: str | None = None
    property_id: str
    tenant_id: str
    owner_id: str
    deposit_payment_id: str | None = None
    property_name: str | None = None
    property_address: str | None = None
    tenant_name: str | None = None
    owner_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def agreement_to_response(agr, prop=None, tenant=None, owner=None) -> dict:
    """Convert an Agreement ORM object to a response dict."""
    return AgreementResponse(
        id=agr.id,
        status=agr.status.value,
        rent_amount=agr.rent_amount,
        security_deposit=agr.security_deposit,
        maintenance_charges=agr.maintenance_charges,
        lease_start=agr.lease_start,
        lease_end=agr.lease_end,
        lease_duration_months=agr.lease_duration_months,
        terms_text=agr.terms_text,
        tenant_signature=agr.tenant_signature,
        owner_signature=agr.owner_signature,
        tenant_signed_at=agr.tenant_signed_at,
        owner_signed_at=agr.owner_signed_at,
        pdf_url=agr.pdf_url,
        property_id=agr.property_id,
        tenant_id=agr.tenant_id,
        owner_id=agr.owner_id,
        deposit_payment_id=agr.deposit_payment_id,
        property_name=prop.name if prop else (agr.property.name if hasattr(agr, 'property') and agr.property else None),
        property_address=prop.address if prop else (agr.property.address if hasattr(agr, 'property') and agr.property else None),
        tenant_name=tenant.name if tenant else (agr.tenant.name if hasattr(agr, 'tenant') and agr.tenant else None),
        owner_name=owner.name if owner else (agr.owner.name if hasattr(agr, 'owner') and agr.owner else None),
        created_at=agr.created_at,
        updated_at=agr.updated_at,
    ).model_dump()
