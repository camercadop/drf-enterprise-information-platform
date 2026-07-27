"""Model for DMS Document Types."""

from django.db import models

from apps.tenants.models import TenantAwareModel


class DocumentType(TenantAwareModel):
    """Document type classification.

    Represents a type of documents within a tenant's DMS.
    """

    name = models.CharField(max_length=100)
    # Display name of the document type (e.g., Invoice, Contract, Report)

    description = models.TextField(blank=True)
    # Optional description of the document type

    class Meta:
        db_table = "dms_document_types"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"], name="unique_document_type_per_tenant"
            )
        ]

    def __str__(self) -> str:
        return str(self.name)
