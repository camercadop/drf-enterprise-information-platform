"""Celery tasks for the event bus — polling and handler dispatch."""

import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.sys_eventbus.envelope import EventEnvelope
from apps.sys_eventbus.models import DeadLetterEvent, ProcessedEvent

logger = logging.getLogger(__name__)


def _max_retries() -> int:
    cfg: dict[str, Any] = getattr(settings, "APP_SYS_EVENTBUS", {})
    return int(cfg.get("MAX_RETRIES", 3))


@shared_task
def poll_eventbus() -> None:
    """Celery beat task — poll the event bus stream and dispatch pending messages.

    Scheduled via ``CELERY_BEAT_SCHEDULE``. Delegates all logic to
    ``poll_stream()`` so this task remains a thin scheduler entry point.
    """
    from apps.sys_eventbus.consumer import poll_stream

    poll_stream()


@shared_task(bind=True)
def dispatch_handler(
    self: Any,
    handler_qualname: str,
    message_id: str,
    envelope_fields: dict[str, str],
) -> None:
    """Execute a single registered handler for an event message.

    Resolves the handler callable from the registry by its qualified name,
    reconstructs the ``EventEnvelope``, and calls the handler. On success,
    records a ``ProcessedEvent`` to prevent re-execution. On failure, retries
    with exponential backoff up to ``MAX_RETRIES``. After exhausting retries,
    writes a ``DeadLetterEvent`` for manual inspection.

    Args:
        handler_qualname: Fully qualified name of the handler function
            (e.g. ``"apps.dms_documents.event_handlers.on_document_created"``).
        message_id: Redis Stream message ID of the originating message.
        envelope_fields: Flat string dict as stored in the Redis Stream entry.
    """
    if ProcessedEvent.objects.filter(message_id=message_id).exists():
        logger.info(
            "Handler already processed message_id=%s handler=%s",
            message_id,
            handler_qualname,
        )
        return

    handler = _resolve_handler(handler_qualname)
    if handler is None:
        logger.warning(
            "Handler not found in registry handler=%s message_id=%s",
            handler_qualname,
            message_id,
        )
        return

    envelope = EventEnvelope.from_redis_fields(envelope_fields)

    try:
        handler(envelope)
        ProcessedEvent.objects.create(
            message_id=message_id,
            event_type=envelope.type,
        )
        logger.info(
            "Handler succeeded handler=%s message_id=%s event_type=%s",
            handler_qualname,
            message_id,
            envelope.type,
        )
    except Exception as exc:
        attempt = self.request.retries + 1
        max_retries = _max_retries()

        if attempt < max_retries:
            logger.warning(
                "Handler failed, retrying handler=%s message_id=%s attempt=%d error=%s",
                handler_qualname,
                message_id,
                attempt,
                str(exc),
            )
            raise self.retry(exc=exc, countdown=2**attempt) from exc

        logger.error(
            "Handler exhausted retries, moving to DLQ handler=%s message_id=%s error=%s",
            handler_qualname,
            message_id,
            str(exc),
        )
        DeadLetterEvent.objects.create(
            message_id=message_id,
            event_type=envelope.type,
            payload=envelope_fields,
            tenant_id=envelope.tenant_id or None,
            error=str(exc),
            retries=attempt,
            failed_at=timezone.now(),
        )


def _resolve_handler(qualname: str) -> Any:
    """Look up a handler callable in the registry by its qualified name.

    Iterates all registered handlers across all event types. Returns the first
    match or ``None`` if not found. The registry is small and in-memory so
    linear scan is acceptable.

    Args:
        qualname: The ``__qualname__`` of the handler function to resolve.

    Returns:
        The handler callable, or ``None`` if not registered.
    """
    from apps.sys_eventbus.registry import _registry

    for handlers in _registry.values():
        for handler in handlers:
            if handler.__qualname__ == qualname:
                return handler
    return None
