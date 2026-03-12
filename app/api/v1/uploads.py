"""
LuxeLife API — File upload routes.

Handles image and document uploads to Google Cloud Storage.
"""

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.responses import success_response
from app.dependencies import get_current_user
from app.models.user import User
from app.services.storage_service import StorageService

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image")
async def upload_image(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WebP, max 5MB)"),
    folder: str = "images",
    _user: User = Depends(get_current_user),
):
    """
    Upload an image to cloud storage.

    Returns the public URL for use in property listings, avatars, etc.
    """
    url = await StorageService.upload_image(file, folder=folder)
    return success_response({"url": url})


@router.post("/document")
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, JPEG, PNG, max 10MB)"),
    folder: str = "documents",
    _user: User = Depends(get_current_user),
):
    """
    Upload a document to cloud storage.

    Used for KYC documents, inspection reports, etc.
    """
    url = await StorageService.upload_document(file, folder=folder)
    return success_response({"url": url})
