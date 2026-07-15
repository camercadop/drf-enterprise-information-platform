"""Serializers for the iam_roles app."""

from typing import Any

from rest_framework import serializers

from core.base.serializers import DefaultModelSerializer

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

    def do_validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Prevent kind mutation on update."""
        if self.instance and "kind" in attrs:
            raise serializers.ValidationError(
                {"kind": "This field cannot be changed after creation."}
            )
        return attrs
