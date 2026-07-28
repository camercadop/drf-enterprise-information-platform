"""Views for DMS Metadata."""

from apps.dms_metadata.models import MetadataDefinition
from apps.dms_metadata.serializers import MetadataDefinitionSerializer
from core.base.views import BaseViewSet


class MetadataDefinitionViewSet(BaseViewSet):
    """CRUD for MetadataDefinition nested under a document type within a tenant."""

    queryset = MetadataDefinition.objects.all()
    parent_lookup_fields = {"document_type_id": "document_type_id"}
    serializer_class = MetadataDefinitionSerializer
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["code"]
