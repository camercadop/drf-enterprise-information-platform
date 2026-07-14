"""Tenant-scoped manager for ORM-level data isolation.

Provides a second enforcement layer (independent of view-level filtering)
as required by ADR-004. Reads the tenant_id from context and filters
querysets automatically.
"""

from typing import Any

from django.db import models

from core.base.context import get_bound_scope


class TenantQuerySet(models.QuerySet[Any]):
    """QuerySet that supports explicit unscoping."""

    def unscoped(self) -> TenantQuerySet:
        """Return the queryset without tenant filtering.

        Use for legitimate cross-tenant access (management commands,
        platform-level admin). Cross-tenant access must be explicit
        per ADR-004.
        """
        return self


class TenantManager(models.Manager[Any]):
    """Manager that automatically filters by the active tenant.

    Behavior:
        - Reads tenant_id from the current context.
        - Filters the queryset by tenant_id.
        - If no tenant is bound, raises RuntimeError (fail-loud per ADR-005).

    The existing TenantFilterBackend (view layer) is the first enforcement
    layer. This manager is the second, independent layer.
    """

    def get_queryset(self) -> TenantQuerySet:
        """Return a queryset filtered by the active tenant.

        Raises:
            RuntimeError: If no tenant is bound in the current context.
                Use .unscoped() for intentional cross-tenant access.
        """
        qs = TenantQuerySet(self.model, using=self._db)
        scope = get_bound_scope()

        tenant_id = scope.get("tenant_id")
        if tenant_id:
            filtered: TenantQuerySet = qs.filter(tenant_id=tenant_id)
            return filtered

        raise RuntimeError(
            f"No tenant scope bound for {self.model.__name__}. "
            f"Use .unscoped() for intentional cross-tenant access."
        )

    def unscoped(self) -> TenantQuerySet:
        """Return an unfiltered queryset, bypassing tenant enforcement.

        Use for management commands, migrations, and platform-level
        operations that legitimately need cross-tenant access.
        """
        return TenantQuerySet(self.model, using=self._db)
