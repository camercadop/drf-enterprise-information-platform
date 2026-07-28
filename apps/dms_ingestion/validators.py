"""Validators for DMS Ingestion.

Pure functions — no DB access. Each raises ValidationError on failure.
Checks are skipped when the corresponding allowed list is empty (no restriction).
"""

import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError

from core.utils.formatting import format_human_size

logger = logging.getLogger(__name__)


def validate_file_size(size: int) -> None:
    """Raise ValidationError if size exceeds the configured maximum.

    Args:
        size: File size in bytes as declared by the client.

    Raises:
        ValidationError: When size exceeds APP_DMS_INGESTION["MAX_FILE_SIZE_BYTES"].
    """
    max_size: int = settings.APP_DMS_INGESTION["MAX_FILE_SIZE_BYTES"]
    if size > max_size:
        logger.warning("File size %s exceeds maximum allowed %s bytes", size, max_size)
        raise ValidationError(
            f"File size {format_human_size(size)} exceeds the maximum allowed {format_human_size(max_size)}."
        )


def validate_mime_type(mime_type: str) -> None:
    """Raise ValidationError if mime_type is not in the allowed list.

    Skips the check when ALLOWED_MIME_TYPES is empty (no restriction configured).

    Args:
        mime_type: MIME type string declared by the client.

    Raises:
        ValidationError: When mime_type is not in APP_DMS_INGESTION["ALLOWED_MIME_TYPES"].
    """
    allowed: list[str] = settings.APP_DMS_INGESTION["ALLOWED_MIME_TYPES"]
    if allowed and mime_type not in allowed:
        logger.warning("MIME type %s is not allowed", mime_type)
        raise ValidationError(f"MIME type '{mime_type}' is not allowed.")


def validate_extension(filename: str) -> None:
    """Raise ValidationError if the file extension is not in the allowed list.

    Skips the check when ALLOWED_EXTENSIONS is empty (no restriction configured).

    Args:
        filename: Original filename as declared by the client.

    Raises:
        ValidationError: When the extension is not in APP_DMS_INGESTION["ALLOWED_EXTENSIONS"].
    """
    allowed: list[str] = settings.APP_DMS_INGESTION["ALLOWED_EXTENSIONS"]
    if not allowed:
        return
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in allowed:
        logger.warning(
            "File extension %s is not allowed for filename %s", ext, filename
        )
        raise ValidationError(f"File extension '{ext}' is not allowed.")
