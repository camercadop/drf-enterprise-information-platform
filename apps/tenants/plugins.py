"""Serializer plugins for tenant boundary enforcement."""

from typing import Any

from django.db import models

from apps.tenants.utils import get_tenant_id
from core.base.serializers import BaseSerializer, SerializerPlugin
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
