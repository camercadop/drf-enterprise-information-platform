import uuid

from django.db import models


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the tenant
    name = models.CharField(max_length=255)
    # Display name of the tenant
    code = models.CharField(max_length=100, unique=True)
    # Internal code for programmatic reference
    is_active = models.BooleanField(default=True)
    # Whether the tenant is currently active
    config = models.JSONField(default=dict, blank=True)
    # Flexible key-value configuration for tenant-specific settings
    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the tenant was created
    updated_at = models.DateTimeField(auto_now=True)
    # Timestamp when the tenant was last updated

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return str(self.name)
