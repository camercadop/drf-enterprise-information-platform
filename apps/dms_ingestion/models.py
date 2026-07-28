"""Models for DMS Ingestion."""

from django.db import models

from apps.iam_users.models import User
from apps.tenants.models import TenantAwareModel


class UploadSession(TenantAwareModel):
    """Tracks a single file upload lifecycle before a Document is created.

    Owns everything from session creation through pipeline completion.
    Has no FK to Document — dms_documents creates the Document upon
    receiving the document.created event published by this module.
    """

    class State(models.TextChoices):
        NEW = "NEW", "New"
        UPLOAD_REQUESTED = "UPLOAD_REQUESTED", "Upload Requested"
        UPLOADING = "UPLOADING", "Uploading"
        UPLOADED = "UPLOADED", "Uploaded"
        VALIDATING = "VALIDATING", "Validating"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        DOCUMENT_CREATED = "DOCUMENT_CREATED", "Document Created"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"
        QUARANTINED = "QUARANTINED", "Quarantined"

    title = models.CharField(max_length=255)
    # Human-readable title that will become the Document title

    document_type = models.CharField(max_length=100, null=True, blank=True)
    # Document type code provided by the client at session creation

    filename = models.CharField(max_length=255)
    # Original filename as declared by the client

    mime_type = models.CharField(max_length=100)
    # MIME type declared by the client at session creation

    size = models.PositiveBigIntegerField()
    # Declared file size in bytes

    checksum = models.CharField(max_length=64, null=True, blank=True)
    # SHA-256 hex digest of the file content, set by ChecksumProcessor

    extension = models.CharField(max_length=20, null=True, blank=True)
    # File extension derived from filename, set by MetadataProcessor

    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.NEW,
    )
    # Current state in the upload session lifecycle

    storage_key = models.CharField(max_length=500, null=True, blank=True)
    # Backend-specific key or path set after the file is written to storage

    error_detail = models.TextField(null=True, blank=True)
    # Human-readable failure reason set when state transitions to FAILED or QUARANTINED

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # User who initiated the upload session

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # User who last updated the session

    class Meta:
        db_table = "dms_ingestion_upload_sessions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"UploadSession({self.id}, {self.state})"
