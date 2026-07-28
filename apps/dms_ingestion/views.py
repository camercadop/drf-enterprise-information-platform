"""Views for DMS Ingestion."""

import logging

from rest_framework import mixins, status
from rest_framework.parsers import FileUploadParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dms_ingestion.models import UploadSession
from apps.dms_ingestion.serializers import (
    UploadSessionCreateSerializer,
    UploadSessionSerializer,
)
from apps.dms_ingestion.storage import get_storage_backend
from apps.dms_ingestion.tasks import run_pipeline_task
from apps.tenants.utils import get_tenant_id
from core.base.views import BaseReadOnlyViewSet

logger = logging.getLogger(__name__)


class UploadSessionViewSet(mixins.CreateModelMixin, BaseReadOnlyViewSet):
    """Create, list, and retrieve upload sessions for the current tenant."""

    queryset = UploadSession.objects.all()
    serializer_class = UploadSessionSerializer
    serializer_classes = {
        "create": UploadSessionCreateSerializer,
    }
    ordering = ["-created_at"]


class UploadView(APIView):
    """Accept a raw file upload for an existing upload session.

    Writes the file to storage, transitions the session to UPLOADED,
    and enqueues the processing pipeline. Returns immediately — pipeline
    result is not awaited.
    """

    parser_classes = [FileUploadParser]

    def put(self, request: Request, pk: str) -> Response:
        """Write the uploaded file to storage and enqueue the pipeline.

        Args:
            request: Authenticated DRF request carrying the raw file.
            pk: UUID string of the target UploadSession.

        Returns:
            204 No Content on success.
            404 if the session does not exist.
            400 if no file is provided in the request.
        """
        try:
            session = UploadSession.objects.get(pk=pk, tenant_id=get_tenant_id(request))
        except UploadSession.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"file": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        storage = get_storage_backend()
        storage_key = storage.save(str(session.id), file)

        session.storage_key = storage_key
        session.state = UploadSession.State.UPLOADED
        session.save(update_fields=["storage_key", "state", "updated_at"])

        run_pipeline_task.delay(str(session.id))

        logger.info("File uploaded for session %s, pipeline enqueued", session.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
