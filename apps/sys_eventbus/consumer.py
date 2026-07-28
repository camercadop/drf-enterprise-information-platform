"""Event bus consumer — reads from the Redis Stream and dispatches to handlers."""

import logging
from typing import Any

from django.conf import settings

from apps.sys_eventbus.envelope import EventEnvelope
from apps.sys_eventbus.models import ProcessedEvent
from apps.sys_eventbus.registry import get_handlers
from core.utils.redis import get_redis_client

logger = logging.getLogger(__name__)


def _config() -> dict[str, Any]:
    config: dict[str, Any] = getattr(settings, "APP_SYS_EVENTBUS", {})
    return config


def _ensure_group(stream: str, group: str) -> None:
    """Create the consumer group if it does not already exist.

    Uses ``XGROUP CREATE ... MKSTREAM`` so the stream is also created if absent.
    Safe to call on every poll — ``BUSYGROUP`` errors are swallowed silently.

    Args:
        stream: Redis Stream key name.
        group: Consumer group name.
    """
    client = get_redis_client()
    try:
        client.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info("Consumer group created stream=%s group=%s", stream, group)
    except Exception as exc:
        if "BUSYGROUP" in str(exc):
            pass
        else:
            raise


def poll_stream() -> None:
    """Read a batch of messages from the stream and dispatch each to its handlers.

    Delivery guarantee is at-most-once: messages are acknowledged before handler
    execution. Idempotency is enforced downstream by ``ProcessedEvent``.

    For each message:
    - Skip if already recorded in ``ProcessedEvent`` (idempotency guard).
    - Skip with a warning if no handlers are registered for the event type.
    - Dispatch each handler as an async Celery task via ``dispatch_handler.delay``.
    - Acknowledge the message immediately after dispatching.
    """
    from apps.sys_eventbus.tasks import dispatch_handler

    cfg = _config()
    stream: str = cfg.get("STREAM_NAME", "sys:eventbus")
    group: str = cfg.get("CONSUMER_GROUP", "sys_eventbus_group")
    consumer: str = cfg.get("CONSUMER_NAME", "sys_eventbus_consumer")
    batch_size: int = int(cfg.get("BATCH_SIZE", 100))

    _ensure_group(stream, group)

    client = get_redis_client()
    results: list[Any] = client.xreadgroup(  # type: ignore[assignment]
        group, consumer, {stream: ">"}, count=batch_size, block=0
    )

    if not results:
        return

    for _stream_key, messages in results:
        for message_id, fields in messages:
            if ProcessedEvent.objects.filter(message_id=message_id).exists():
                logger.info(
                    "Skipping already-processed message message_id=%s", message_id
                )
                client.xack(stream, group, message_id)
                continue

            envelope = EventEnvelope.from_redis_fields(fields)
            handlers = get_handlers(envelope.type)

            if not handlers:
                logger.warning(
                    "No handlers registered for event_type=%s message_id=%s",
                    envelope.type,
                    message_id,
                )
                client.xack(stream, group, message_id)
                continue

            for handler in handlers:
                dispatch_handler.delay(handler.__qualname__, message_id, fields)

            client.xack(stream, group, message_id)
            logger.info(
                "Message dispatched message_id=%s event_type=%s handlers=%d",
                message_id,
                envelope.type,
                len(handlers),
            )
