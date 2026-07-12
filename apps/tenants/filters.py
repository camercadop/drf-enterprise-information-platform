"""Tenant-scoping filter backend."""

from typing import Any

from django.db.models import QuerySet
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request


class TenantFilterBackend(BaseFilterBackend):
    """Automatically scopes querysets to the authenticated user's tenant.

    Behavior:
        - If the model has a `tenant_id` field and the view has not opted out,
          filters the queryset by the tenant_id claim from the JWT.
        - If the model is tenant-scoped but no tenant_id claim is present,
          returns an empty queryset (denial per ADR-004).
        - If the model has no `tenant_id` field, or the view sets
          `tenant_scoping = False`, this is a no-op.
    """

    def filter_queryset(
        self, request: Request, queryset: QuerySet[Any], view: Any
    ) -> QuerySet[Any]:
        if getattr(view, "tenant_scoping", True) is False:
            return queryset

        model = queryset.model
        if not hasattr(model, "tenant_id"):
            return queryset

        tenant_id = self._get_tenant_id(request)
        if not tenant_id:
            return queryset.none()

        return queryset.filter(tenant_id=tenant_id)

    def _get_tenant_id(self, request: Request) -> str | None:
        """Extract tenant_id from JWT claims."""
        if request.auth and hasattr(request.auth, "get"):
            result: str | None = request.auth.get("tenant_id")
            return result
        return None
