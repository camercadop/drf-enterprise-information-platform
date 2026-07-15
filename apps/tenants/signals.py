"""Signals for the tenants app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.iam_roles.models import TenantRole
from apps.sys_permissions.catalog import get_default_role_permissions
from apps.tenants.models import Tenant


@receiver(post_save, sender=Tenant)
def seed_default_roles(
    sender: type[Tenant], instance: Tenant, created: bool, **kwargs: object
) -> None:
    """Create default roles with permissions when a new tenant is created."""
    if not created:
        return

    role_permissions = get_default_role_permissions()
    for role_name, permissions in role_permissions.items():
        TenantRole.objects.create(
            tenant=instance,
            name=role_name.capitalize(),
            kind=role_name,
            description=f"Default {role_name} role",
            permissions=permissions,
        )
