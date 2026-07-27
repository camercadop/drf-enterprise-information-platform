"""Core document model for the DMS."""

from django.db import models

from apps.dms_document_types.models import DocumentType
from apps.iam_users.models import User
from apps.tenants.models import TenantAwareModel


class Document(TenantAwareModel):
    """A document owned by a tenant, with metadata and lifecycle state.

    Versioning is handled separately by DocumentVersion.
    """

    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    # Classification of the document (e.g. Invoice, Contract)

    title = models.CharField(
        max_length=255,
    )
    # Human-readable name of the document

    description = models.TextField(
        null=True,
        blank=True,
    )
    # Long-form description of the document

    class Availability(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    availability = models.CharField(
        max_length=20,
        choices=Availability.choices,
        default=Availability.ACTIVE,
    )
    # Lifecycle state of the document

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    # Timestamp when the document was archived

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # User responsible for this document

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # User who created this document

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # User who last updated this document

    class Meta:
        db_table = "dms_documents"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "title"],
                name="unique_document_title_per_tenant",
            )
        ]

    def __str__(self) -> str:
        return str(self.title)
