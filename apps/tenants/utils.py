"""Tenant context utilities for extracting tenant info from requests."""

from rest_framework.request import Request

from apps.tenants.models import TenantSetting


def get_tenant_id(request: Request) -> str | None:
    """Extract tenant_id from the JWT token claims.

    Args:
        request: The DRF request object.
    """
    if request.auth and hasattr(request.auth, "get"):
        result: str | None = request.auth.get("tenant_id")
        return result
    return None


def get_tenant_setting(
    tenant_id: str, key: str, default: str | None = None
) -> str | None:
    """Get a single tenant setting value by key.

    Args:
        tenant_id: The tenant UUID.
        key: The setting key to look up.
        default: Value to return if the setting does not exist.
    """
    setting = TenantSetting.objects.filter(tenant_id=tenant_id, key=key).first()
    return setting.value if setting else default


def get_tenant_settings(tenant_id: str, prefix: str = "") -> dict[str, str]:
    """Get all tenant settings, optionally filtered by key prefix."""
    qs = TenantSetting.objects.filter(tenant_id=tenant_id)
    if prefix:
        qs = qs.filter(key__startswith=prefix)
    return {s.key: s.value for s in qs}
