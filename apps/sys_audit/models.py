"""Audit log model — append-only record of state-changing operations."""

import uuid

from django.conf import settings
from django.db import models


class AuditLogManager(models.Manager["AuditLog"]):
    """Manager that enforces append-only semantics.

    Only exposes create and read operations. Update and delete are
    prohibited at the application layer per ADR-009.
    """

    def update(self, **kwargs: object) -> int:
        """Blocked — audit records are immutable."""
        raise NotImplementedError("Audit records are immutable.")

    def delete(self) -> tuple[int, dict[str, int]]:
        """Blocked — audit records cannot be deleted."""
        raise NotImplementedError("Audit records cannot be deleted.")


class AuditLog(models.Model):
    """Immutable record of a state-changing operation.

    Stores who did what, to which resource, within what tenant boundary,
    and what changed. Satisfies ADR-009 mandatory rules.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the audit record

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    # The user who performed the action

    action = models.CharField(max_length=50)
    # The type of operation performed

    target_type = models.CharField(max_length=255)
    # The model label of the affected resource (e.g., "tenants.Team")

    target_id = models.UUIDField()
    # The primary key of the affected resource

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    # The tenant boundary context (null for non-tenant-scoped resources)

    changes = models.JSONField(default=dict)
    # Full payload on create, field diff on update, empty on delete

    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the operation was recorded

    objects = AuditLogManager()

    class Meta:
        db_table = "sys_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "created_at"],
                name="idx_audit_tenant_time",
            ),
            models.Index(
                fields=["target_type", "target_id"],
                name="idx_audit_target",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.target_type}:{self.target_id} by {self.actor_id}"

    def save(self, *args: object, **kwargs: object) -> None:
        """Only allow save on new records (insert). Updates are blocked."""
        if not self._state.adding:
            raise NotImplementedError("Audit records are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        """Blocked — audit records cannot be deleted."""
        raise NotImplementedError("Audit records cannot be deleted.")
