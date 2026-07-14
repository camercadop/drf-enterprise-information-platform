"""Audit logging helper for recording state-changing operations."""

from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model

from apps.sys_audit.models import AuditLog

User = get_user_model()


def log_audit(
    *,
    actor: Any,
    action: str,
    target_type: str,
    target_id: UUID,
    tenant_id: str | UUID | None = None,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    """Record an audit entry for a state-changing operation.

    This is the single entry point for writing audit records. Used by
    the AuditPlugin and available for direct use in background tasks,
    management commands, or any context with a declared actor.

    Args:
        actor: The user instance who performed the action.
        action: Operation name (e.g., "create", "update", "delete", "login", "password_change").
        target_type: Model label (e.g., "tenants.Team").
        target_id: Primary key of the affected resource.
        tenant_id: Tenant boundary UUID, or None for non-tenant resources.
        changes: Payload dict — full data on create, diff on update, empty on delete.

    Returns:
        The created AuditLog instance.
    """
    entry: AuditLog = AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        tenant_id=tenant_id,
        changes=changes or {},
    )
    return entry
