"""
Models for DMS Metadata.
"""

from django.db import models

from apps.tenants.models import TenantAwareModel

from .metadata_types import MetadataType
from .validators import validate_default_value, validate_validation_rules


class MetadataDefinition(TenantAwareModel):
    """Definition of a metadata field for documents within a tenant."""

    code = models.CharField(
        max_length=100,
    )
    # Unique code for programmatic reference (e.g., "author_name")

    name = models.CharField(
        max_length=255,
    )
    # Human-readable name of the metadata field (e.g., "Author Name")

    document_type = models.ForeignKey(
        "dms_document_types.DocumentType",
        on_delete=models.CASCADE,
        related_name="metadata_definitions",
        db_index=True,
    )
    # Document type this metadata definition applies to

    data_type = models.CharField(
        max_length=20,
        choices=MetadataType.choices,
        db_index=True,
    )
    # Data type of the metadata field

    required = models.BooleanField(
        default=False,
    )
    # Whether this metadata field is required for documents

    searchable = models.BooleanField(
        default=False,
    )
    # Whether this metadata field can be used in search queries

    filterable = models.BooleanField(
        default=False,
    )
    # Whether this metadata field can be used in filters

    sortable = models.BooleanField(
        default=False,
    )
    # Whether this metadata field can be used for sorting

    indexed = models.BooleanField(
        default=False,
    )
    # Whether this metadata field is indexed for faster lookups

    default_value = models.JSONField(
        null=True,
        blank=True,
    )
    # Default value for this metadata field

    validation_rules = models.JSONField(
        null=True,
        blank=True,
    )
    # Validation rules specific to the data_type

    class Meta:
        db_table = "dms_metadata_definitions"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "document_type", "code"],
                name="unique_metadata_definition_per_tenant_and_document_type",
            ),
        ]


    def __str__(self) -> str:
        return f"{self.code} ({self.document_type}) - {self.name}"

    def clean(self) -> None:
        """Validate validation_rules structure and default_value against type and rules.

        Called by full_clean() before saving. Ensures validation_rules conform
        to the expected schema for the data_type, and that default_value satisfies
        both the type and the rules when both are present.
        """
        super().clean()

        if self.validation_rules is not None:
            validate_validation_rules(self.data_type, self.validation_rules)

        if self.default_value is not None:
            validate_default_value(self.data_type, self.default_value, self.validation_rules)
