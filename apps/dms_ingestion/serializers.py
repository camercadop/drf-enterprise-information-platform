"""Serializers for DMS Ingestion."""

from rest_framework import serializers

from apps.dms_document_types.models import DocumentType
from apps.dms_ingestion.models import UploadSession
from apps.tenants.utils import get_tenant_id
from core.base.serializers import DefaultModelSerializer


class UploadSessionCreateSerializer(DefaultModelSerializer):
    """Accepts client input to create a new upload session.

    State is set to NEW by the model default and is not writable by the client.
    Storage key, checksum, and extension are set by the pipeline — not accepted
    on creation.
    """

    class Meta:
        model = UploadSession
        fields = [
            "id",
            "title",
            "document_type",
            "filename",
            "mime_type",
            "size",
        ]

    def validate_document_type(self, value: str) -> str:
        """Validate that a DocumentType with the given name exists for the current tenant.

        Performs a case-insensitive lookup scoped to the request tenant. Stores
        the canonical name from the database on success.

        Args:
            value: The document type name provided by the client.

        Returns:
            The canonical DocumentType name as stored in the database.

        Raises:
            ValidationError: If no matching DocumentType is found for this tenant.
        """
        if not value:
            return value
        request = self.context["request"]
        try:
            doc_type = DocumentType.objects.get(
                tenant_id=get_tenant_id(request),
                name__iexact=value,
            )
        except DocumentType.DoesNotExist as err:
            raise serializers.ValidationError(
                f"Document type '{value}' does not exist."
            ) from err
        return str(doc_type.name)


class UploadSessionSerializer(DefaultModelSerializer):
    """Read serializer for list and retrieve actions on upload sessions."""

    class Meta:
        model = UploadSession
        fields = [
            "id",
            "title",
            "document_type",
            "filename",
            "mime_type",
            "size",
            "checksum",
            "extension",
            "state",
            "storage_key",
            "error_detail",
            "created_at",
            "updated_at",
        ]
