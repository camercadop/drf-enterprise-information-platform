"""Serializers for Document Types."""

from core.base.serializers import DefaultModelSerializer
from core.validators.serializers import UniqueTogetherContextValidator

from .models import DocumentType


class DocumentTypeSerializer(DefaultModelSerializer):
    """Serializer for DMSDocumentType create and update operations."""

    class Meta:
        model = DocumentType
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ]
        validators = [
            UniqueTogetherContextValidator(
                fields={"name": "name"},
                message="A document type with this name already exists in this tenant.",
            ),
        ]
