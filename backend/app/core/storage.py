"""Image and file storage service with local-disk implementation and abstraction interface."""
import os
import uuid
from typing import Optional
from starlette import status

from app.core.config import get_settings
from app.core.exceptions import AppHTTPException

settings = get_settings()


class StorageService:
    """Storage interface for catalog media assets."""

    def __init__(self, upload_dir: Optional[str] = None, max_mb: Optional[int] = None):
        self.upload_dir = upload_dir or settings.UPLOAD_DIR
        self.max_mb = max_mb or settings.MAX_UPLOAD_MB
        self.max_bytes = self.max_mb * 1024 * 1024

    def detect_image_extension(self, file_bytes: bytes) -> str:
        """Detect allowed image type (JPEG, PNG, WebP) from magic bytes only.

        Rejects any unrecognized or dangerous format with 422 invalid_image.
        """
        if len(file_bytes) < 12:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid image format. Allowed formats are JPEG, PNG, and WebP.",
                code="invalid_image",
            )

        # JPEG: starts with FF D8 FF
        if file_bytes[:3] == b"\xff\xd8\xff":
            return ".jpg"

        # PNG: starts with 89 50 4E 47 0D 0A 1A 0A
        if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return ".png"

        # WebP: starts with RIFF....WEBP
        if file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
            return ".webp"

        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid image format. Only JPEG, PNG, and WebP images are allowed.",
            code="invalid_image",
        )

    def save_image(self, file_bytes: bytes, content_type: Optional[str] = None) -> str:
        """Validate size & magic bytes, save to disk under server-generated UUID, return relative path."""
        if len(file_bytes) > self.max_bytes:
            raise AppHTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed upload size of {self.max_mb}MB.",
                code="file_too_large",
            )

        ext = self.detect_image_extension(file_bytes)
        filename = f"{uuid.uuid4().hex}{ext}"
        relative_path = f"parts/{filename}"

        full_path = os.path.abspath(os.path.join(self.upload_dir, relative_path))
        base_dir = os.path.abspath(self.upload_dir)

        # Path traversal guard
        if not full_path.startswith(base_dir):
            raise AppHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path destination.",
                code="invalid_path",
            )

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_bytes)

        return relative_path

    def delete(self, relative_path: Optional[str]) -> None:
        """Delete file at relative path with path traversal protection. Ignore if absent."""
        if not relative_path:
            return

        full_path = os.path.abspath(os.path.join(self.upload_dir, relative_path))
        base_dir = os.path.abspath(self.upload_dir)

        # Prevent directory traversal attacks
        if not full_path.startswith(base_dir):
            return

        try:
            if os.path.isfile(full_path):
                os.remove(full_path)
        except OSError:
            pass

    def public_url(self, relative_path: Optional[str]) -> Optional[str]:
        """Generate public URL for the stored asset."""
        if not relative_path:
            return None
        cleaned = relative_path.replace("\\", "/").lstrip("/")
        return f"/uploads/{cleaned}"


# Singleton instance for route handlers and services
storage_service = StorageService()

