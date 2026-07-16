"""Audit plugins for serializer and viewset lifecycle boundaries."""

from typing import Any

from django.db import models

from apps.sys_audit.services import log_audit
from apps.tenants.utils import get_tenant_id
from core.base.plugins import SerializerPlugin, ViewSetPlugin
from core.base.serializers import BaseSerializer


class AuditSerializerPlugin(SerializerPlugin):
    """Records audit logs on create, update, and destroy operations.

    Attaches at declared lifecycle boundaries per ADR-008. Extracts
    actor and tenant context from the serializer's request.
    """

    def _get_actor(self, serializer: BaseSerializer) -> Any:
        """Extract the authenticated user from serializer context."""
        request = serializer.context.get("request")
        if request and hasattr(request, "user"):
            return request.user
        return None

    def _get_tenant_id(self, serializer: BaseSerializer) -> str | None:
        """Extract tenant_id from the request's JWT claims."""
        request = serializer.context.get("request")
        if not request:
            return None
        return get_tenant_id(request)

    def _get_target_type(self, serializer: BaseSerializer) -> str:
        """Return the model label (e.g., 'tenants.Team')."""
        model: type[models.Model] = serializer.Meta.model  # type: ignore[attr-defined]
        label: str = model._meta.label_lower
        return label

    def on_post_create(
        self, serializer: BaseSerializer, instance: models.Model
    ) -> None:
        actor = self._get_actor(serializer)
        if not actor:
            return

        log_audit(
            actor=actor,
            action="create",
            target_type=self._get_target_type(serializer),
            target_id=instance.pk,
            tenant_id=self._get_tenant_id(serializer),
            changes=serializer.to_representation(instance),
        )

    def on_post_update(
        self, serializer: BaseSerializer, instance: models.Model
    ) -> None:
        actor = self._get_actor(serializer)
        if not actor:
            return

        log_audit(
            actor=actor,
            action="update",
            target_type=self._get_target_type(serializer),
            target_id=instance.pk,
            tenant_id=self._get_tenant_id(serializer),
            changes=self._build_update_diff(serializer, instance),
        )

    def _build_update_diff(
        self, serializer: BaseSerializer, instance: models.Model
    ) -> dict[str, Any]:
        """Build a diff of changed fields from validated_data.

        Returns a dict mapping field names to {"old": ..., "new": ...}.
        """
        diff: dict[str, Any] = {}
        validated_data: dict[str, Any] = getattr(serializer, "_validated_data", {})
        for field_name, new_value in validated_data.items():
            old_value = getattr(instance, field_name, None)
            if old_value != new_value:
                diff[field_name] = {"old": str(old_value), "new": str(new_value)}
        return diff


class AuditViewSetPlugin(ViewSetPlugin):
    """Records audit log on destroy operations.

    Destroy is handled at the viewset level because the serializer's
    create/update lifecycle does not cover deletion.
    """

    def on_post_destroy(self, viewset: Any, instance: models.Model) -> None:
        """Log a delete audit entry after successful destruction."""
        request = getattr(viewset, "request", None)
        if not request or not hasattr(request, "user") or not request.user:
            return

        model: type[models.Model] = type(instance)
        target_type: str = model._meta.label_lower

        log_audit(
            actor=request.user,
            action="delete",
            target_type=target_type,
            target_id=instance.pk,
            tenant_id=get_tenant_id(request),
        )
