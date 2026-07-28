"""Serializers for documents."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.dms_documents.models import Document
from apps.dms_metadata.services import MetadataValidationService
from core.base.serializers import DefaultModelSerializer


class DocumentSerializer(DefaultModelSerializer):
    """Serializer for Document model."""

    class Meta:
        model = Document
        fields = [
            "id",
            "document_type",
            "title",
            "description",
            "metadata",
            "availability",
            "owner",
        ]

    def do_validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate metadata against the document type's MetadataDefinition rules.

        Delegates to MetadataValidationService when both document_type and a
        non-empty metadata dict are present. Skips validation when either is
        absent — metadata is optional and document_type is nullable.

        Args:
            attrs: The validated field values.

        Returns:
            The unchanged attrs dict if validation passes.

        Raises:
            serializers.ValidationError: If metadata violates any definition rule.
        """
        document_type = attrs.get("document_type")
        metadata = attrs.get("metadata")

        if document_type:
            if metadata is None:
                raise serializers.ValidationError(
                    {"metadata": "metadata is required when document_type is provided."}
                )
            try:
                MetadataValidationService.validate(document_type, metadata)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"metadata": e.message}) from e

        return attrs
