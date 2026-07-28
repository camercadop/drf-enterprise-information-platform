"""Models for sys_eventbus — idempotency tracking and dead letter queue."""

import uuid

from django.db import models


class ProcessedEvent(models.Model):
    """Records successfully processed stream message IDs.

    Used to enforce idempotency — the consumer checks this table before
    dispatching a message to its handler. If the message ID is already
    present, the message is skipped.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for this record

    message_id = models.CharField(max_length=255, unique=True)
    # Redis Stream message ID (e.g. "1700000000000-0")

    event_type = models.CharField(max_length=255)
    # Event type string (e.g. "document.created")

    processed_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the message was successfully processed

    class Meta:
        db_table = "sys_eventbus_processed_event"
        indexes = [
            models.Index(fields=["message_id"], name="idx_processed_event_message_id"),
        ]

    def __str__(self) -> str:
        return f"ProcessedEvent({self.event_type}, {self.message_id})"


class DeadLetterEvent(models.Model):
    """Records messages that exhausted all retry attempts.

    Preserved for manual inspection and resolution. Never deleted by
    application logic — operators resolve entries by reprocessing or
    discarding them explicitly.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for this record

    message_id = models.CharField(max_length=255)
    # Original Redis Stream message ID

    event_type = models.CharField(max_length=255)
    # Event type string (e.g. "document.created")

    payload = models.JSONField()
    # Full event envelope preserved for inspection and potential reprocessing

    tenant_id = models.UUIDField(null=True, blank=True)
    # Tenant boundary context — null for non-tenant-scoped events

    error = models.TextField()
    # Last exception message recorded before exhausting retries

    retries = models.PositiveIntegerField()
    # Number of dispatch attempts made before moving to DLQ

    failed_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the message was moved to the DLQ

    class Meta:
        db_table = "sys_eventbus_dead_letter_event"
        ordering = ["-failed_at"]
        indexes = [
            models.Index(fields=["event_type"], name="idx_dlq_event_type"),
            models.Index(fields=["tenant_id"], name="idx_dlq_tenant_id"),
        ]

    def __str__(self) -> str:
        return f"DeadLetterEvent({self.event_type}, {self.message_id})"
