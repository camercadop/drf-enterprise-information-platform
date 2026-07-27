"""Views for DMS Document Types."""

from apps.dms_document_types.models import DocumentType
from core.base.views import BaseViewSet

from .serializers import DocumentTypeSerializer


class DocumentTypeViewSet(BaseViewSet):
    """CRUD for document types within a tenant."""

    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
