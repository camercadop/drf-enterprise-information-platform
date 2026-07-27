"""Serializers for documents."""

from apps.dms_documents.models import Document
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
            "availability",
            "owner",
        ]
