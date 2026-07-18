"""Services for reading and writing per-user, per-tenant attributes."""

import logging
from typing import TYPE_CHECKING

from .models import UserTenantAttribute

if TYPE_CHECKING:
    from apps.iam_users.models import User
    from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def get_attribute(user: User, tenant: Tenant, attribute: str, default: str | None = None) -> str | None:
    """Return the value of a user-tenant attribute, or `default` if not set.

    Args:
        user: The user to look up.
        tenant: The tenant scope.
        attribute: The attribute name.
        default: Value to return when the attribute does not exist.

    Returns:
        The stored string value, or `default` if the attribute does not exist.
    """
    entry = UserTenantAttribute.objects.filter(
        user=user, tenant=tenant, attribute=attribute
    ).first()
    return entry.value if entry else default


def set_attribute(user: User, tenant: Tenant, attribute: str, value: str) -> None:
    """Create or update a user-tenant attribute.

    Uses update_or_create so callers do not need to check existence first.

    Args:
        user: The user to set the attribute for.
        tenant: The tenant scope.
        attribute: The attribute name.
        value: The value to store as text.
    """
    UserTenantAttribute.objects.update_or_create(
        user=user,
        tenant=tenant,
        attribute=attribute,
        defaults={"value": value},
    )
    logger.info(
        "User attribute set user_id=%s tenant_id=%s attribute=%s",
        user.pk,
        tenant.pk,
        attribute,
    )


def delete_attribute(user: User, tenant: Tenant, attribute: str) -> None:
    """Delete a user-tenant attribute if it exists.

    Silently does nothing if the attribute is not set. Use this to clear
    an attribute rather than setting a sentinel value.

    Args:
        user: The user to clear the attribute for.
        tenant: The tenant scope.
        attribute: The attribute name to delete.
    """
    deleted, _ = UserTenantAttribute.objects.filter(
        user=user, tenant=tenant, attribute=attribute
    ).delete()
    if deleted:
        logger.info(
            "User attribute deleted user_id=%s tenant_id=%s attribute=%s",
            user.pk,
            tenant.pk,
            attribute,
        )
