"""Views for DMS Documents."""

from apps.dms_documents.models import Document
from apps.dms_documents.serializers import DocumentSerializer
from core.base.views import BaseViewSet


class DocumentViewSet(BaseViewSet):
    """Full CRUD for Documents within a tenant."""

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    search_fields = ["title", "description"]
    ordering_fields = ["title", "created_at"]
    ordering = ["-created_at"]
