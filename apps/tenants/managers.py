"""Tenant-scoped manager for ORM-level data isolation.

Provides a second enforcement layer (independent of view-level filtering)
as required by ADR-004. Reads the tenant_id from the bound scope and
filters querysets automatically.
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
        - Reads tenant_id from the current scope (bound by TenantJWTAuthentication).
        - If scope is bound, filters the queryset by tenant_id.
        - If no scope is bound (CLI, admin, migrations), returns an
          unfiltered queryset. The view-layer TenantFilterBackend provides
          isolation for API requests independently.

    The two layers together satisfy ADR-004's defense-in-depth requirement:
    both must fail for data to leak across tenant boundaries.
    """

    def get_queryset(self) -> TenantQuerySet:
        """Return a queryset filtered by the active tenant when scope is bound."""
        qs = TenantQuerySet(self.model, using=self._db)
        scope = get_bound_scope()

        tenant_id = scope.get("tenant_id")
        if tenant_id:
            filtered: TenantQuerySet = qs.filter(tenant_id=tenant_id)
            return filtered

        return qs

    def unscoped(self) -> TenantQuerySet:
        """Return an unfiltered queryset, bypassing tenant enforcement.

        Use for management commands, migrations, and platform-level
        operations that legitimately need cross-tenant access.
        """
        return TenantQuerySet(self.model, using=self._db)
