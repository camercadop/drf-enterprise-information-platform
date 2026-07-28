"""Event bus publisher — writes domain events to the Redis Stream."""

import logging
from typing import Any

from django.conf import settings
from rest_framework.request import Request

from apps.sys_eventbus.envelope import EventEnvelope
from apps.tenants.utils import get_tenant_id
from core.utils.redis import get_redis_client

logger = logging.getLogger(__name__)


def _stream_name() -> str:
    """Return the configured stream name from APP_SYS_EVENTBUS settings.

    Returns:
        Stream name string (e.g. ``"sys:eventbus"``).
    """
    config: dict[str, Any] = getattr(settings, "APP_SYS_EVENTBUS", {})
    return str(config.get("STREAM_NAME", "sys:eventbus"))


def publish_event_from_request(
    event_type: str,
    payload: dict[str, Any],
    request: Request,
) -> str:
    """Publish a domain event using tenant and actor context from a DRF request.

    Convenience wrapper around ``publish()`` for use at view and serializer
    lifecycle boundaries. Extracts ``tenant_id`` from ``request.tenant_id`` and
    ``actor_id`` from ``request.user.pk``.

    Args:
        event_type: Dot-namespaced event type (e.g. ``"document.created"``).
        payload: JSON-serializable domain-specific event data.
        request: Authenticated DRF request carrying tenant and user context.

    Returns:
        The Redis-generated message ID (e.g. ``"1700000000000-0"``).

    Raises:
        redis.RedisError: If the write to Redis fails.
    """
    return publish(
        event_type=event_type,
        payload=payload,
        tenant_id=get_tenant_id(request),
        actor_id=str(request.user.pk),
    )


def publish(
    *,
    event_type: str,
    payload: dict[str, Any],
    tenant_id: str | None = None,
    actor_id: str | None = None,
) -> str:
    """Publish a domain event to the event bus stream.

    Builds an ``EventEnvelope``, serializes it to a flat Redis-compatible
    dict, and appends it to the stream via ``XADD``. Non-blocking — returns
    immediately after Redis confirms the write.

    Use this function at declared lifecycle boundaries (hooks, plugins) per
    ADR-008. Do not call from inside business logic or validation methods.

    Args:
        event_type: Dot-namespaced event type (e.g. ``"document.created"``).
        payload: JSON-serializable domain-specific event data.
        tenant_id: Tenant boundary UUID string. None for platform-level events.
        actor_id: UUID string of the actor that triggered the event.

    Returns:
        The Redis-generated message ID (e.g. ``"1700000000000-0"``).

    Raises:
        redis.RedisError: If the write to Redis fails.
    """
    envelope = EventEnvelope(
        type=event_type,
        payload=payload,
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    client = get_redis_client()
    stream = _stream_name()
    message_id: str = client.xadd(stream, envelope.to_redis_fields())  # type: ignore[arg-type, assignment]
    logger.info(
        "Event published stream=%s type=%s message_id=%s tenant_id=%s",
        stream,
        event_type,
        message_id,
        tenant_id,
    )
    return message_id
