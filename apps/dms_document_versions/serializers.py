"""Serializers for DMS document versions."""

from typing import Any

from apps.dms_document_versions.models import DocumentVersion
from core.base.serializers import DefaultModelSerializer


class DocumentVersionSerializer(DefaultModelSerializer):
    """Serializer for creating and retrieving document versions."""

    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "document",
            "version",
            "filename",
            "mime_type",
            "extension",
            "checksum",
            "size",
            "storage_state",
            "created_by",
            "created_at",
        ]

    def pre_create(self, validated_data: dict[str, Any]) -> None:
        document = validated_data["document"]
        last = DocumentVersion.objects.filter(document=document).order_by("-version").first()
        validated_data["version"] = (last.version + 1) if last else 1

