"""Serializers for the tenant_settings app."""

import json
from typing import Any

import jsonschema
from rest_framework import serializers

from apps.tenant_settings.catalog import get_merged_catalog
from apps.tenants.models import TenantSetting


class TenantSettingListSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Lightweight serializer for listing non-private tenant settings."""

    namespace = serializers.SerializerMethodField()

    class Meta:
        model = TenantSetting
        fields = ["key", "namespace", "value"]

    def get_namespace(self, obj: TenantSetting) -> str | None:
        """Derive namespace from the catalog entry for this setting key."""
        entry = get_merged_catalog().get(obj.key)
        return entry.get("namespace") if entry else None


class TenantSettingSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Serializer for TenantSetting retrieve and partial-update operations.

    `key` is read-only — lookup and updates are performed by key via the URL.
    `namespace` is derived from the catalog and exposed read-only.
    On write, coerces the value to the declared type and validates it against
    the entry's JSON Schema if one is provided.
    `tenant` is injected server-side by TenantInjectionSerializerPlugin.
    """

    namespace = serializers.SerializerMethodField()

    class Meta:
        model = TenantSetting
        fields = ["key", "namespace", "value"]
        read_only_fields = ["key"]

    def get_namespace(self, obj: TenantSetting) -> str | None:
        """Derive namespace from the catalog entry for this setting key."""
        entry = get_merged_catalog().get(obj.key)
        return entry.get("namespace") if entry else None

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Coerce and validate value against the catalog entry.

        Resolves the key from the instance (update only). Coerces the value
        string to the declared type, then validates against the entry's JSON
        Schema if present. Raises ValidationError on any violation.
        """
        key: str = self.instance.key  # type: ignore[union-attr]
        value = attrs.get("value")

        entry = get_merged_catalog().get(key)
        if entry is None or entry.get("private", False):
            raise serializers.ValidationError({"key": "Unknown setting key."})

        if value is not None:
            coerced = self._coerce(value, entry["type"], key)
            json_schema = entry.get("schema")
            if json_schema:
                try:
                    jsonschema.validate(coerced, json_schema)
                except jsonschema.ValidationError as e:
                    raise serializers.ValidationError(
                        {"value": e.message}
                    ) from e

        return attrs

    def _coerce(self, value: str, setting_type: str, key: str) -> Any:
        """Coerce a string value to the declared catalog type.

        Args:
            value: Raw string value from the request.
            setting_type: One of 'string', 'integer', 'boolean', 'json'.
            key: Setting key, used in error messages.

        Returns:
            The coerced Python value.

        Raises:
            ValidationError: If the value cannot be coerced to the declared type.
        """
        if setting_type == "json":
            try:
                return json.loads(value)
            except (ValueError, TypeError) as e:
                raise serializers.ValidationError(
                    {"value": f"'{key}' expects a valid JSON string."}
                ) from e
        if setting_type == "integer":
            try:
                return int(value)
            except (ValueError, TypeError) as e:
                raise serializers.ValidationError(
                    {"value": f"'{key}' expects an integer value."}
                ) from e
        if setting_type == "boolean":
            if value.lower() in ("true", "1"):
                return True
            if value.lower() in ("false", "0"):
                return False
            raise serializers.ValidationError(
                {"value": f"'{key}' expects a boolean value (true/false)."}
            )
        return value
