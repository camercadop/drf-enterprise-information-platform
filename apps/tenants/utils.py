"""Tenant context utilities for extracting tenant info from requests."""

from rest_framework.request import Request

from apps.tenant_settings.catalog import get_merged_catalog
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


def get_tenant_setting(tenant_id: str, key: str) -> str | None:
    """Get a single tenant setting value by key.

    Falls back to the catalog default when no DB record exists.
    Returns None if the key is not in the catalog.

    Args:
        tenant_id: The tenant UUID.
        key: The setting key to look up.

    Returns:
        The setting value as a string, or None if not found.
    """
    setting = TenantSetting.objects.filter(tenant_id=tenant_id, key=key).first()
    if setting:
        return str(setting.value) if setting.value is not None else None
    entry = get_merged_catalog().get(key)
    return str(entry["default"]) if entry else None


def get_tenant_settings(tenant_id: str, prefix: str = "") -> dict[str, str]:
    """Get all tenant settings, optionally filtered by key prefix.

    Merges catalog defaults for keys matching the prefix that have no DB record.

    Args:
        tenant_id: The tenant UUID.
        prefix: Optional key prefix to filter results.
    """
    qs = TenantSetting.objects.filter(tenant_id=tenant_id)
    if prefix:
        qs = qs.filter(key__startswith=prefix)
    saved = {s.key: s.value for s in qs}
    catalog = get_merged_catalog()
    for key, entry in catalog.items():
        if key not in saved and (not prefix or key.startswith(prefix)):
            saved[key] = entry["default"]
    return saved
