"""
LuxeLife API — Google Cloud Storage service.

Handles file uploads (images, documents) to GCS.
Falls back to local file storage in development mode.
"""

import uuid
from pathlib import Path

import structlog
from fastapi import UploadFile

from app.config import settings
from app.core.exceptions import BadRequestError

logger = structlog.get_logger()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOC_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5 MB
MAX_DOC_SIZE = 10 * 1024 * 1024    # 10 MB


class StorageService:
    """Google Cloud Storage file management."""

    _client = None
    _bucket = None

    @classmethod
    def _get_bucket(cls):
        """Lazy-initialize the GCS client and bucket."""
        if cls._bucket is None:
            if not settings.GCS_CREDENTIALS_JSON:
                logger.warning("GCS credentials not configured — using local storage")
                return None
            try:
                from google.cloud import storage
                cls._client = storage.Client.from_service_account_json(
                    settings.GCS_CREDENTIALS_JSON
                )
                cls._bucket = cls._client.bucket(settings.GCS_BUCKET)
                logger.info("GCS bucket connected", bucket=settings.GCS_BUCKET)
            except Exception as e:
                logger.error("GCS connection failed", error=str(e))
                return None
        return cls._bucket

    @classmethod
    async def upload_image(cls, file: UploadFile, folder: str = "images") -> str:
        """
        Upload an image to GCS.

        Validates file type and size.
        Returns the public URL.
        """
        # Validate type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise BadRequestError(
                f"Invalid image type: {file.content_type}. "
                f"Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )

        # Read and validate size
        contents = await file.read()
        if len(contents) > MAX_IMAGE_SIZE:
            raise BadRequestError(
                f"Image too large: {len(contents)} bytes. Max: {MAX_IMAGE_SIZE} bytes"
            )

        # Generate unique filename
        ext = file.filename.rsplit(".", 1)[-1] if file.filename else "jpg"
        key = f"{folder}/{uuid.uuid4().hex}.{ext}"

        return cls._upload(key, contents, file.content_type)

    @classmethod
    async def upload_document(cls, file: UploadFile, folder: str = "documents") -> str:
        """
        Upload a document (PDF, image) to GCS.

        Validates file type and size.
        Returns the public URL.
        """
        if file.content_type not in ALLOWED_DOC_TYPES:
            raise BadRequestError(
                f"Invalid document type: {file.content_type}. "
                f"Allowed: {', '.join(ALLOWED_DOC_TYPES)}"
            )

        contents = await file.read()
        if len(contents) > MAX_DOC_SIZE:
            raise BadRequestError(
                f"Document too large: {len(contents)} bytes. Max: {MAX_DOC_SIZE} bytes"
            )

        ext = file.filename.rsplit(".", 1)[-1] if file.filename else "pdf"
        key = f"{folder}/{uuid.uuid4().hex}.{ext}"

        return cls._upload(key, contents, file.content_type)

    @classmethod
    def _upload(cls, key: str, contents: bytes, content_type: str) -> str:
        """Upload bytes to GCS or local fallback."""
        bucket = cls._get_bucket()

        if bucket is None:
            # Local fallback for development
            local_dir = Path("uploads") / key.rsplit("/", 1)[0]
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = Path("uploads") / key
            local_path.write_bytes(contents)
            url = f"http://localhost:8000/static/{key}"
            logger.info("File saved locally", path=str(local_path))
            return url

        # Upload to GCS
        blob = bucket.blob(key)
        blob.upload_from_string(contents, content_type=content_type)
        blob.make_public()
        url = blob.public_url
        logger.info("File uploaded to GCS", key=key, url=url)
        return url

    @classmethod
    def delete_file(cls, url: str) -> None:
        """Delete a file from GCS by its URL."""
        bucket = cls._get_bucket()
        if bucket is None:
            # Local fallback
            local_path = Path("uploads") / url.split("/static/")[-1]
            if local_path.exists():
                local_path.unlink()
            return

        try:
            # Extract blob key from URL
            prefix = f"https://storage.googleapis.com/{settings.GCS_BUCKET}/"
            if url.startswith(prefix):
                key = url[len(prefix):]
                blob = bucket.blob(key)
                blob.delete()
                logger.info("File deleted from GCS", key=key)
        except Exception as e:
            logger.error("Failed to delete from GCS", url=url, error=str(e))
