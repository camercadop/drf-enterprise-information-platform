"""Serializers for the iam_roles app."""

from typing import Any

from rest_framework import serializers

from apps.sys_permissions.catalog import get_merged_catalog
from core.base.serializers import DefaultModelSerializer
from core.validators.serializers import UniqueTogetherContextValidator

from .models import TenantRole


class TenantRoleListSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Lightweight serializer for listing roles."""

    class Meta:
        model = TenantRole
        fields = ["id", "name", "kind", "description"]


class TenantRoleSerializer(DefaultModelSerializer):
    """Serializer for TenantRole create and update operations.

    `kind` is writable on creation but immutable after that.
    `tenant` is injected server-side by TenantInjectionSerializerPlugin.
    Roles with kind=viewer cannot be assigned write permissions.
    """

    class Meta:
        model = TenantRole
        fields = [
            "id",
            "name",
            "kind",
            "description",
            "permissions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = [
            UniqueTogetherContextValidator(
                fields={"name": "name"},
                message="A role with this name already exists.",
            ),
        ]

    def do_validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Enforce kind immutability and viewer-kind write permission restriction.

        Raises ValidationError if kind is changed after creation, or if a
        viewer-kind role is assigned a write permission (readonly=False in catalog).
        """
        if self.instance and "kind" in attrs:
            raise serializers.ValidationError(
                {"kind": "This field cannot be changed after creation."}
            )

        kind = attrs.get("kind") or (self.instance.kind if self.instance else None)

        permissions: dict[str, Any] = attrs.get("permissions", {})

        if kind == TenantRole.Kind.VIEWER and permissions:
            catalog = get_merged_catalog()

            # Collect non-readonly codenames.
            write_codenames = {
                codename
                for codename, action in catalog.items()
                if not action.get("readonly", False)
            }
            violations = [
                c for c, v in permissions.items() if v >= 1 and c in write_codenames
            ]
            if violations:
                raise serializers.ValidationError(
                    {
                        "permissions": "Viewer roles cannot be assigned write permissions."
                    }
                )

        return attrs
