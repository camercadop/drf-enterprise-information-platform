"""Views for DMS Document Versions."""

from rest_framework import mixins

from apps.dms_document_versions.models import DocumentVersion
from apps.dms_document_versions.serializers import DocumentVersionSerializer
from core.base.views import BaseReadOnlyViewSet


class DocumentVersionViewSet(mixins.CreateModelMixin, BaseReadOnlyViewSet):
    """CRUD for DocumentVersion within a tenant."""

    queryset = DocumentVersion.objects.all()
    parent_lookup_fields = {"document_id": "document_id"}
    serializer_class = DocumentVersionSerializer
    search_fields = []
    ordering_fields = ["version", "created_at"]
    ordering = ["-created_at"]
