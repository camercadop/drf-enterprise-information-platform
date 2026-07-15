"""Permission class factory for RBAC enforcement.

Provides HasTenantPermission, a factory that generates DRF permission
classes checking whether the user's role in the current tenant grants
a specific permission codename.
"""

from typing import Any

from rest_framework.request import Request

from apps.tenants.utils import get_tenant_id
from core.permissions.base import BasePermission


def HasTenantPermission(codename: str) -> type[BasePermission]:
    """Create a permission class that checks a specific permission codename.

    The generated class checks whether the authenticated user's role in the
    current tenant (from JWT) includes the given codename. Before checking
    the specific codename, it verifies the user has access to the app
    (app_label.access). Users with is_admin=True on their membership bypass
    all checks.

    Args:
        codename: Permission codename to check (e.g., "tenants.teams.create").

    Returns:
        A permission class that enforces the given codename.
    """
    app_label = codename.split(".")[0]
    access_codename = f"{app_label}.access"

    class _Permission(BasePermission):
        message = f"You do not have the '{codename}' permission."

        def has_permission(self, request: Request, view: Any) -> bool:
            if not request.user or not request.user.is_authenticated:
                return False

            tenant_id = get_tenant_id(request)
            if not tenant_id:
                return False

            membership = (
                request.user.memberships.filter(
                    tenant_id=tenant_id,
                    is_active=True,
                )
                .select_related("role")
                .first()
            )
            if not membership:
                return False

            if membership.is_admin:
                return True

            permissions = membership.role.permissions or {}
            if permissions.get(access_codename) != 1:
                return False
            return permissions.get(codename) == 1

    _Permission.__name__ = f"HasTenantPermission_{codename}"
    _Permission.__qualname__ = f"HasTenantPermission_{codename}"
    return _Permission
