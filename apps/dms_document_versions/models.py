"""Document version model for the DMS."""

from django.db import models

from apps.dms_documents.models import Document
from apps.iam_users.models import User
from apps.tenants.models import TenantAwareModel


class DocumentVersion(TenantAwareModel):
    """A versioned snapshot of a document's file within a tenant's account."""

    class StorageState(models.TextChoices):
        PENDING = "PENDING", "Pending"
        UPLOADING = "UPLOADING", "Uploading"
        PROCESSING = "PROCESSING", "Processing"
        AVAILABLE = "AVAILABLE", "Available"
        CORRUPTED = "CORRUPTED", "Corrupted"
        QUARANTINED = "QUARANTINED", "Quarantined"
        ARCHIVED = "ARCHIVED", "Archived"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    # The document this version belongs to

    version = models.PositiveIntegerField(editable=False)
    # Monotonically increasing version number scoped to the document

    filename = models.CharField(max_length=255)
    # Original filename as uploaded by the user

    mime_type = models.CharField(max_length=100, null=True, blank=True)
    # MIME type detected or declared at upload time

    extension = models.CharField(max_length=20, null=True, blank=True, editable=False)
    # File extension derived from the filename

    checksum = models.CharField(max_length=64, null=True, blank=True, editable=False)
    # SHA-256 hex digest of the file content for integrity verification

    size = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    # File size in bytes

    storage_backend = models.CharField(
        max_length=20,
        default="LOCAL",
        editable=False,
    )
    # Storage backend used to persist this version's file

    storage_key = models.CharField(
        max_length=500, null=True, blank=True, editable=False
    )
    # Backend-specific key or path used to retrieve the file

    storage_state = models.CharField(
        max_length=20,
        choices=StorageState.choices,
        default=StorageState.UPLOADING,
        editable=False,
    )
    # Current availability state of the stored file

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )
    # User who uploaded this version

    class Meta:
        db_table = "dms_document_versions"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version"],
                name="unique_version_per_document",
            )
        ]

    def __str__(self) -> str:
        return f"DocumentVersion({self.document_id}, v{self.version})"
