"""
LuxeLife API — KYC routes.
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.permissions import require_roles
from app.core.responses import paginated_response, success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import generate_cuid
from app.models.kyc import KycDocument, KycStatus
from app.models.user import User
from app.services.storage_service import StorageService

router = APIRouter(prefix="/kyc", tags=["KYC"])


@router.get("/me")
async def my_kyc(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get current user's KYC documents and progress."""
    result = await db.execute(select(KycDocument).where(KycDocument.user_id == user.id))
    docs = result.scalars().all()
    return success_response({
        "kyc_progress": user.kyc_progress,
        "documents": [_doc_to_dict(d) for d in docs],
    })


@router.post("/upload", status_code=201)
async def upload_kyc(
    doc_type: str = Query(..., pattern=r"^(aadhaar|pan|passport|bank_statement|address_proof)$"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a KYC document."""
    url = await StorageService.upload_document(file, folder=f"kyc/{user.id}")
    doc = KycDocument(id=generate_cuid(), user_id=user.id, doc_type=doc_type, file_url=url)
    db.add(doc)
    await db.flush()

    # Update KYC progress
    total = (await db.execute(select(func.count(KycDocument.id)).where(KycDocument.user_id == user.id))).scalar() or 0
    approved = (await db.execute(
        select(func.count(KycDocument.id)).where(KycDocument.user_id == user.id, KycDocument.status == KycStatus.APPROVED)
    )).scalar() or 0
    progress = min(int((approved / max(total, 1)) * 100), 100) if total else 0
    user.kyc_progress = progress
    await db.flush()

    return success_response(_doc_to_dict(doc))


@router.get("/pending")
async def pending_reviews(
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all pending KYC reviews. **Admin only.**"""
    query = select(KycDocument).where(KycDocument.status == KycStatus.PENDING)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.order_by(KycDocument.created_at.asc()).offset((page - 1) * limit).limit(limit))
    return paginated_response([_doc_to_dict(d) for d in result.scalars().all()], total, page, limit)


@router.patch("/{doc_id}/review")
async def review_kyc(
    doc_id: str,
    action: str = Query(..., pattern=r"^(approved|rejected)$"),
    rejection_reason: str | None = Query(None),
    admin: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a KYC document. **Admin only.**"""
    doc = await db.get(KycDocument, doc_id)
    if not doc:
        raise NotFoundError("KYC Document")
    doc.status = KycStatus(action)
    doc.reviewed_by = admin.id
    if action == "rejected":
        doc.rejection_reason = rejection_reason
    await db.flush()
    return success_response(_doc_to_dict(doc))


def _doc_to_dict(d: KycDocument) -> dict:
    return {
        "id": d.id, "doc_type": d.doc_type, "file_url": d.file_url,
        "status": d.status.value, "reviewed_by": d.reviewed_by,
        "rejection_reason": d.rejection_reason, "created_at": str(d.created_at),
    }
