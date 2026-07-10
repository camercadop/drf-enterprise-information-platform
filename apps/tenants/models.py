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

    details = models.JSONField(default=dict, blank=True)
    # General tenant metadata (description, industry, contact info, etc.)

    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the tenant was created

    updated_at = models.DateTimeField(auto_now=True)
    # Timestamp when the tenant was last updated

    class Meta:
        db_table = "tenants"
        ordering = ["name"]

    def __str__(self) -> str:
        return str(self.name)


class TenantSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the setting

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="settings"
    )
    # The tenant this setting belongs to

    key = models.CharField(max_length=255)
    # Setting identifier (e.g., password_min_length, feature_flag_x)

    value = models.TextField()
    # The setting value stored as text

    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the setting was created

    updated_at = models.DateTimeField(auto_now=True)
    # Timestamp when the setting was last changed

    class Meta:
        db_table = "tenants_settings"
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "key"], name="unique_setting_per_tenant"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tenant.code}:{self.key}"


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the team

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="teams")
    # The tenant this team belongs to

    name = models.CharField(max_length=255)
    # Display name of the team

    description = models.TextField(blank=True)
    # Optional description of the team's purpose

    is_active = models.BooleanField(default=True)
    # Whether the team is currently active

    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the team was created

    updated_at = models.DateTimeField(auto_now=True)
    # Timestamp when the team was last updated

    class Meta:
        db_table = "tenants_teams"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"], name="unique_team_per_tenant"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant})"
