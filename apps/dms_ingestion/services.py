"""Services for DMS Ingestion.

Orchestrates the upload pipeline: validation, processing, state transitions,
and domain event publishing.
"""

import logging

from django.core.exceptions import ValidationError

from apps.dms_ingestion.models import UploadSession
from apps.dms_ingestion.processors import build_pipeline
from apps.dms_ingestion.storage import get_storage_backend
from apps.dms_ingestion.validators import (
    validate_extension,
    validate_file_size,
    validate_mime_type,
)
from apps.sys_eventbus.publisher import publish

logger = logging.getLogger(__name__)


def run_pipeline(session_id: str) -> None:
    """Run the full ingestion pipeline for an uploaded session.

    Executes validators, then processors, then publishes a document.created
    event. Transitions the session state at each stage. On any failure the
    session is transitioned to FAILED with error_detail set.

    Args:
        session_id: UUID string of the UploadSession to process.

    Raises:
        UploadSession.DoesNotExist: If no session matches session_id.
        ValidationError: If any validator rejects the file.
        Exception: If any processor raises an unexpected error.
    """
    session = UploadSession.objects.get(pk=session_id)
    storage = get_storage_backend()

    if not session.storage_key:
        _fail(session, "No storage key found — file was never written to storage.")
        return

    _transition(session, str(UploadSession.State.VALIDATING))

    try:
        validate_file_size(session.size)
        validate_mime_type(session.mime_type)
        validate_extension(session.filename)
    except ValidationError as exc:
        _fail(session, str(exc))
        raise

    _transition(session, str(UploadSession.State.PROCESSING))

    try:
        with storage.open(session.storage_key) as file:  # type: ignore[arg-type]
            for processor in build_pipeline():
                processor.process(session, file)
    except Exception as exc:
        _fail(session, str(exc))
        raise

    _transition(session, str(UploadSession.State.READY))

    publish(
        event_type="document.created",
        payload={
            "session_id": str(session.id),
            "title": session.title,
            "document_type": session.document_type,
            "filename": session.filename,
            "mime_type": session.mime_type,
            "size": session.size,
            "checksum": session.checksum,
            "extension": session.extension,
            "storage_key": session.storage_key,
        },
        tenant_id=str(session.tenant_id),
        actor_id=str(session.created_by_id) if session.created_by_id else None,
    )

    _transition(session, str(UploadSession.State.DOCUMENT_CREATED))
    logger.info("Pipeline completed for session %s", session_id)


def _transition(session: UploadSession, state: str) -> None:
    """Transition the session to a new state and persist it.

    Args:
        session: The session to update.
        state: The target state.
    """
    session.state = state
    session.save(update_fields=["state", "updated_at"])


def _fail(session: UploadSession, detail: str) -> None:
    """Transition the session to FAILED and record the error detail.

    Args:
        session: The session to update.
        detail: Human-readable description of the failure reason.
    """
    session.state = UploadSession.State.FAILED
    session.error_detail = detail
    session.save(update_fields=["state", "error_detail", "updated_at"])
    logger.warning("Pipeline failed for session %s: %s", session.id, detail)
