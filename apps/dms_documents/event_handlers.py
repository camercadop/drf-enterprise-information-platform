"""Event handlers for the dms_documents app."""

import logging
from typing import Any

from apps.dms_document_types.models import DocumentType
from apps.dms_document_versions.models import DocumentVersion
from apps.dms_documents.models import Document
from apps.sys_eventbus.envelope import EventEnvelope
from apps.sys_eventbus.registry import event_handler

logger = logging.getLogger(__name__)


@event_handler("document.created")
def handle_document_created(envelope: EventEnvelope) -> None:
    """Create a Document and its first DocumentVersion from an ingestion event.

    Triggered when the ingestion pipeline successfully processes an upload session.
    The envelope payload carries all fields needed to create both records — no
    additional DB queries are made beyond the optional DocumentType lookup.

    Expects the following payload keys: session_id, title, document_type,
    filename, mime_type, size, checksum, extension, storage_key.

    Args:
        envelope: The event envelope published by the ingestion pipeline.
    """
    payload: dict[str, Any] = envelope.payload
    tenant_id: str | None = envelope.tenant_id
    actor_id: str | None = envelope.actor_id

    document_type_name: str | None = payload.get("document_type")
    document_type_id: Any = None
    if document_type_name and tenant_id:
        try:
            document_type_id = DocumentType.objects.values_list("id", flat=True).get(
                tenant_id=tenant_id,
                name__iexact=document_type_name,
            )
        except DocumentType.DoesNotExist as err:
            raise ValueError(
                f"DocumentType '{document_type_name}' not found for tenant {tenant_id} "
                f"(session_id={payload.get('session_id')})"
            ) from err

    document = Document.objects.create(
        tenant_id=tenant_id,
        title=payload["title"],
        document_type_id=document_type_id,
        created_by_id=actor_id,
        owner_id=actor_id,
    )

    DocumentVersion.objects.create(
        tenant_id=tenant_id,
        document=document,
        version=1,
        filename=payload["filename"],
        mime_type=payload.get("mime_type"),
        size=payload.get("size"),
        checksum=payload.get("checksum"),
        extension=payload.get("extension"),
        storage_key=payload.get("storage_key"),
        storage_state=DocumentVersion.StorageState.AVAILABLE,
        created_by_id=actor_id,
    )

    logger.info(
        "Document and DocumentVersion created document_id=%s session_id=%s",
        document.pk,
        payload.get("session_id"),
    )
