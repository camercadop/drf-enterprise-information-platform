"""Views for the tenant_settings app."""

from typing import Any, cast

from django.db.models import QuerySet
from rest_framework import mixins
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from apps.tenant_settings.catalog import get_merged_catalog
from apps.tenant_settings.serializers import (
    TenantSettingListSerializer,
    TenantSettingSerializer,
)
from apps.tenants.models import TenantSetting
from apps.tenants.permissions import IsTenantAdmin
from core.base.views import BaseGenericViewSet


class TenantSettingViewSet(
    BaseGenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
):
    """List, retrieve, and partial-update tenant settings.

    Settings are looked up by key. Only non-private settings are exposed.
    List merges catalog defaults with DB records — keys with no saved record
    are returned with their catalog default value. Write access is restricted
    to tenant admins. PUT is disabled — use PATCH.
    """

    queryset = TenantSetting.objects.all()
    serializer_class = TenantSettingSerializer
    serializer_classes = {
        "list": TenantSettingListSerializer,
    }
    write_permission_classes = [IsTenantAdmin]
    lookup_field = "key"
    search_fields = ["key"]
    ordering_fields = ["key", "created_at"]
    ordering = ["key"]
    http_method_names = ["get", "patch", "head", "options"]

    def _public_catalog(self) -> dict[str, dict[str, Any]]:
        """Return only non-private entries from the merged catalog."""
        return {
            key: entry
            for key, entry in get_merged_catalog().items()
            if not entry.get("private", False)
        }

    def _make_default(self, key: str, entry: dict[str, Any]) -> TenantSetting:
        """Build an unsaved TenantSetting from a catalog default.

        Args:
            key: The setting key.
            entry: The catalog entry for that key.

        Returns:
            An unsaved TenantSetting instance with the catalog default value.
        """
        return TenantSetting(key=key, value=entry["default"])

    def get_queryset(self) -> QuerySet[TenantSetting]:
        """Scope queryset to public catalog keys only."""
        return super().get_queryset().filter(key__in=self._public_catalog().keys())

    def get_object(self) -> TenantSetting:
        """Return the DB record for the key, or a default instance if absent."""
        catalog = self._public_catalog()
        key: str = self.kwargs[self.lookup_field]
        if key not in catalog:
            raise NotFound()
        try:
            return cast(TenantSetting, super().get_object())
        except Exception:
            return self._make_default(key, catalog[key])

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Return all public catalog keys merged with saved DB records.

        Keys with no DB record are returned with their catalog default value.
        Response is unpaginated.
        """
        catalog = self._public_catalog()
        saved: dict[str, TenantSetting] = {
            s.key: s for s in self.get_queryset()
        }
        instances = [
            saved.get(key) or self._make_default(key, entry)
            for key, entry in catalog.items()
        ]
        serializer = TenantSettingListSerializer(instances, many=True, context=self.get_serializer_context())
        return Response(serializer.data)
