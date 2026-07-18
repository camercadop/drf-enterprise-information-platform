"""Tenant plugins for serializer and viewset lifecycle boundaries."""

from typing import Any

from django.db import models

from apps.tenants.utils import get_tenant_id
from core.base.plugins import SerializerPlugin, ViewSetPlugin
from core.base.serializers import BaseSerializer
from core.exceptions.api import PermissionDeniedError


class TenantInjectionSerializerPlugin(SerializerPlugin):
    """Derives tenant_id server-side from JWT claims.

    - on_pre_create: injects tenant_id into validated_data. Fails fast if
      the model requires a tenant but no claim is present.
    - on_pre_update: strips tenant_id from validated_data if present, or
      raises if the value differs from the instance's current tenant.
    """

    def _get_tenant_id(self, serializer: BaseSerializer) -> str | None:
        """Extract tenant_id from the serializer's request context."""
        request = serializer.context.get("request")
        if not request:
            return None
        return get_tenant_id(request)

    def _model_has_tenant(self, serializer: BaseSerializer) -> bool:
        model: type[models.Model] = serializer.Meta.model  # type: ignore[attr-defined]
        return hasattr(model, "tenant_id")

    def on_pre_create(
        self, serializer: BaseSerializer, validated_data: dict[str, Any]
    ) -> None:
        if not self._model_has_tenant(serializer):
            return

        tenant_id = self._get_tenant_id(serializer)
        if not tenant_id:
            raise PermissionDeniedError("No tenant context in token.")

        validated_data["tenant_id"] = tenant_id

    def on_pre_update(
        self,
        serializer: BaseSerializer,
        instance: models.Model,
        validated_data: dict[str, Any],
    ) -> None:
        if not self._model_has_tenant(serializer):
            return

        if "tenant_id" in validated_data:
            current_tenant_id = str(instance.tenant_id)  # type: ignore[attr-defined]
            if validated_data["tenant_id"] != current_tenant_id:
                raise PermissionDeniedError(
                    "Tenant reassignment is not allowed."
                )
            del validated_data["tenant_id"]


class TenantContextViewSetPlugin(ViewSetPlugin):
    """Injects tenant_id into serializer context and scopes querysets by tenant.

    This makes tenant_id available to serializer-level validators
    (e.g., UniqueTogetherContextValidator) before validation runs.

    on_get_queryset scopes the queryset to the requesting user's tenant.
    Superusers bypass filtering and receive the full queryset. Returns
    qs.none() when no tenant context is present for non-superusers.
    """

    def on_build_context(self, viewset: Any, context: dict[str, Any]) -> None:
        """Add tenant_id to serializer context."""
        request = context.get("request")
        if not request:
            return
        tenant_id = get_tenant_id(request)
        if tenant_id:
            context["tenant_id"] = tenant_id

    def filter_queryset(
        self, viewset: Any, qs: models.QuerySet[Any]
    ) -> models.QuerySet[Any]:
        """Filter queryset by tenant unless the requesting user is a superuser.

        Args:
            viewset: The viewset instance handling the request.
            qs: The base queryset to filter.

        Returns:
            The original queryset for superusers, a tenant-filtered queryset
            for tenant users, or qs.none() when no tenant context is present.
        """
        request = viewset.request
        if request.user.is_superuser:
            return qs
        tenant_id = get_tenant_id(request)
        if not tenant_id:
            return qs.none()
        return qs.filter(tenant_id=tenant_id)
