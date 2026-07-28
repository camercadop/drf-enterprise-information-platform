"""Event envelope — standard shape for all domain events on the bus."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class EventEnvelope:
    """Standard envelope for all events published to the event bus.

    Every event published to ``sys:eventbus`` is wrapped in this envelope.
    Consumers receive the full envelope — handlers access ``payload`` for
    domain-specific data and the top-level fields for routing and context.

    Args:
        type: Dot-namespaced event type string (e.g. ``"document.created"``).
        payload: Domain-specific event data. Must be JSON-serializable.
        tenant_id: Tenant boundary context. None for platform-level events.
        actor_id: UUID string of the user or system identity that triggered the event.
        id: Auto-generated UUID string. Override only in tests.
        published_at: ISO 8601 UTC timestamp. Auto-set to now if not provided.
    """

    type: str
    payload: dict[str, Any]
    tenant_id: str | None = None
    actor_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    published_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_redis_fields(self) -> dict[str, str]:
        """Serialize the envelope to a flat string dict for Redis Streams.

        Redis Streams store entries as flat key/value string pairs. Nested
        structures (``payload``) are JSON-encoded into a single string field.

        Returns:
            Flat dict of string keys and string values suitable for ``XADD``.
        """
        import json

        return {
            "id": self.id,
            "type": self.type,
            "tenant_id": self.tenant_id or "",
            "actor_id": self.actor_id or "",
            "payload": json.dumps(self.payload),
            "published_at": self.published_at,
        }

    @classmethod
    def from_redis_fields(cls, fields: dict[str, str]) -> EventEnvelope:
        """Deserialize an envelope from Redis Stream entry fields.

        Inverse of ``to_redis_fields``. Called by the consumer when reading
        messages from the stream.

        Args:
            fields: Flat string dict as returned by ``redis-py`` stream reads.

        Returns:
            Reconstructed ``EventEnvelope`` instance.
        """
        import json

        return cls(
            id=fields["id"],
            type=fields["type"],
            tenant_id=fields["tenant_id"] or None,
            actor_id=fields["actor_id"] or None,
            payload=json.loads(fields["payload"]),
            published_at=fields["published_at"],
        )
