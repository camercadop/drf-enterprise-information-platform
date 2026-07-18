"""Models for user event tracking and authentication attempt logging."""

import uuid

from django.conf import settings
from django.db import models


class UserEvent(models.Model):
    """Behavioral event emitted by an authenticated user.

    Records user-initiated actions such as login, logout, password change,
    and membership transitions. Actor uses SET_NULL to preserve the record
    after user deletion; user_email provides a denormalized identity reference.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the event record

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_events",
    )
    # The user who triggered the event; nullable to survive user deletion

    user_email = models.EmailField()
    # Denormalized email for identity reference after actor deletion

    category = models.CharField(max_length=50)
    # Logical grouping of the event (e.g., "auth", "membership")

    event = models.CharField(max_length=50)
    # Specific event name within the category (e.g., "login", "logout")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_events",
    )
    # Tenant boundary context; null for non-tenant-scoped events

    metadata = models.JSONField(default=dict)
    # Event-specific payload (e.g., IP address, session count)

    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the event was recorded

    class Meta:
        db_table = "sys_user_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "created_at"], name="idx_user_event_actor_time"),
            models.Index(fields=["tenant", "created_at"], name="idx_user_event_tenant_time"),
            models.Index(fields=["category", "event"], name="idx_user_event_category_event"),
        ]

    def __str__(self) -> str:
        return f"{self.category}.{self.event} by {self.user_email}"


class AuthAttemptLog(models.Model):
    """Record of a login attempt regardless of outcome.

    Captures every authentication attempt for security monitoring and
    brute-force forensics. Not tied to an authenticated actor — attempts
    may come from unknown or deleted users.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the attempt record

    email = models.EmailField()
    # Email submitted in the login attempt

    ip_address = models.CharField(max_length=45)
    # IP address of the requester (supports IPv4 and IPv6)

    success = models.BooleanField()
    # Whether the attempt resulted in a successful authentication

    failure_reason = models.CharField(max_length=100, blank=True)
    # Machine-readable reason for failure (e.g., "invalid_credentials", "account_locked")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="auth_attempts",
    )
    # Resolved tenant context at the time of the attempt

    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the attempt was recorded

    class Meta:
        db_table = "sys_auth_attempts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "created_at"], name="idx_auth_attempt_email_time"),
            models.Index(fields=["ip_address", "created_at"], name="idx_auth_attempt_ip_time"),
        ]

    def __str__(self) -> str:
        outcome = "success" if self.success else f"failed:{self.failure_reason}"
        return f"AuthAttempt {self.email} {outcome}"
