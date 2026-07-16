"""Tenant-scoped permission classes."""

from typing import Any

from rest_framework.request import Request

from apps.tenants.utils import get_tenant_id
from core.permissions.base import BasePermission


class IsTenantAdmin(BasePermission):
    """Permission that allows access only to tenant admins.

    Checks whether the authenticated user has is_admin=True on their
    active membership for the current tenant (extracted from JWT).
    """

    message = "You must be a tenant admin to perform this action."

    def has_permission(self, request: Request, view: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            self._log_denied(request, view, "User is not authenticated.")
            return False

        tenant_id = get_tenant_id(request)
        if not tenant_id:
            self._log_denied(request, view, "No tenant context in token.")
            return False

        allowed: bool = request.user.memberships.filter(
            tenant_id=tenant_id,
            is_active=True,
            is_admin=True,
        ).exists()
        if not allowed:
            self._log_denied(request, view)
        return allowed

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        return self.has_permission(request, view)
