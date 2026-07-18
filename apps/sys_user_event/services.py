"""Service functions for recording user events."""

from typing import Any
from uuid import UUID

from apps.sys_user_event.models import UserEvent


def record_event(
    *,
    actor: Any,
    user_email: str = "",
    category: str,
    event: str,
    tenant_id: str | UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> UserEvent:
    """Record a user-initiated behavioral event.

    Single entry point for writing UserEvent records. Call this directly
    from views, signals, or background tasks whenever a user performs a
    tracked action.

    Args:
        actor: The user instance who triggered the event, or None if deleted.
        user_email: Denormalized email for identity reference. Derived from
            actor.email when not provided.
        category: Logical grouping (e.g., "auth", "membership").
        event: Specific event name within the category (e.g., "login", "logout").
        tenant_id: Tenant boundary UUID, or None for non-tenant-scoped events.
        metadata: Optional event-specific payload.

    Returns:
        The created UserEvent instance.
    """
    resolved_email: str = user_email or (getattr(actor, "email", "") or "")
    entry: UserEvent = UserEvent.objects.create(
        actor=actor,
        user_email=resolved_email,
        category=category,
        event=event,
        tenant_id=tenant_id,
        metadata=metadata or {},
    )
    return entry
