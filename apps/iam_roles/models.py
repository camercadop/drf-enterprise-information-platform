"""Tenant-scoped role definitions for RBAC."""

from django.db import models

from apps.tenants.models import TenantAwareModel


class TenantRole(TenantAwareModel):
    """Tenant-specific role definitions for RBAC.

    Each tenant has its own set of roles. Default roles (Owner, Admin,
    Member, Viewer) are seeded on tenant creation. Custom roles can be
    created by tenant admins.
    """

    class Kind(models.TextChoices):
        OWNER = "owner"
        ADMIN = "admin"
        MEMBER = "member"
        VIEWER = "viewer"
        CUSTOM = "custom"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="roles",
        db_index=True,
    )
    # The tenant this role belongs to

    name = models.CharField(max_length=50)
    # Display name of the role (e.g. Owner, Admin, Member, Viewer)

    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.CUSTOM)
    # Internal semantic type — determines business rule enforcement

    description = models.TextField(blank=True)
    # Optional explanation of what this role grants

    permissions = models.JSONField(default=dict)
    # Dict mapping permission codenames to grant values

    class Meta:
        db_table = "iam_roles"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"], name="unique_role_per_tenant"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant})"
