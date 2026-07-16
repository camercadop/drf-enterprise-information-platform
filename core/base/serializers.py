"""
Base serializers for the enterprise platform.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.utils.module_loading import import_string
from django.utils.text import slugify
from rest_framework import serializers

from core.base.plugins import SerializerPlugin


class BaseSerializer(serializers.ModelSerializer):
    """
    Base serializer with plugin system and template method lifecycle.
    """

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        abstract = True

        # Per-serializer plugins added to the global set.
        extensions: list[type[SerializerPlugin]] = []

        # Plugins to exclude from the resolved set (global or local).
        extensions_exclude: list[type[SerializerPlugin]] = []

    # --- Plugin dispatch ---

    def _get_plugins(self) -> list[SerializerPlugin]:
        """Resolve the final plugin list for this serializer.

        Merge strategy:
            final = (global from settings.DEFAULT_SERIALIZER_PLUGINS)
                  + (local from Meta.extensions)
                  - (excluded from Meta.extensions_exclude)

        Global plugins are loaded by dotted path from the Django setting
        DEFAULT_SERIALIZER_PLUGINS. They apply to every serializer that inherits
        from BaseSerializer. Each plugin decides internally whether to act
        (e.g., by inspecting the model).

        Local plugins are declared per-serializer via Meta.extensions.

        Exclusions allow a serializer to opt out of specific global or
        local plugins via Meta.extensions_exclude.

        Execution order: global plugins first (in setting order), then
        local plugins (in declaration order).
        """
        rest_framework: dict[str, Any] = getattr(settings, "REST_FRAMEWORK", {})
        global_paths: list[str] = rest_framework.get("DEFAULT_SERIALIZER_PLUGINS", [])
        global_plugins: list[type[SerializerPlugin]] = [
            import_string(path) for path in global_paths
        ]
        local_plugins: list[type[SerializerPlugin]] = getattr(
            self.Meta, "extensions", []
        )
        excluded: list[type[SerializerPlugin]] = getattr(
            self.Meta, "extensions_exclude", []
        )
        merged = global_plugins + local_plugins
        return [plugin() for plugin in merged if plugin not in excluded]

    def _run_plugins(self, hook: str, *args: Any, **kwargs: Any) -> None:
        """Execute a named hook on all resolved plugins.

        Args:
            hook: The plugin method name to invoke.
            *args: Positional arguments forwarded to the hook.
            **kwargs: Keyword arguments forwarded to the hook.
        """
        for plugin in self._get_plugins():
            if hasattr(plugin, hook):
                getattr(plugin, hook)(self, *args, **kwargs)

    # --- Create lifecycle ---

    def create(self, validated_data: dict[str, Any]) -> models.Model:
        """Create a model instance with full plugin and hook execution.

        Subclasses should not override this method. Use pre_create/do_create/post_create
        hooks or plugins instead.
        """
        self._run_plugins("on_pre_create", validated_data)
        self.pre_create(validated_data)
        instance = self.do_create(validated_data)
        self.post_create(instance, validated_data)
        self._run_plugins("on_post_create", instance)
        return instance

    def pre_create(self, validated_data: dict[str, Any]) -> None:
        """Hook called before do_create. Override to prepare data."""

    def do_create(self, validated_data: dict[str, Any]) -> models.Model:
        """Perform the actual model creation and save."""
        instance = self.Meta.model(**validated_data)  # type: ignore[attr-defined]
        instance.save()
        return instance

    def post_create(
        self, instance: models.Model, validated_data: dict[str, Any]
    ) -> None:
        """Hook called after do_create. Override for side effects."""

    # --- Update lifecycle ---

    def update(
        self, instance: models.Model, validated_data: dict[str, Any]
    ) -> models.Model:
        """Update a model instance with full plugin and hook execution.

        Subclasses should not override this method. Use pre_update/do_update/post_update
        hooks or plugins instead.
        """
        self._run_plugins("on_pre_update", instance, validated_data)
        self.pre_update(instance, validated_data)
        instance = self.do_update(instance, validated_data)
        self.post_update(instance, validated_data)
        self._run_plugins("on_post_update", instance)
        return instance

    def pre_update(
        self, instance: models.Model, validated_data: dict[str, Any]
    ) -> None:
        """Hook called before do_update. Override to prepare data."""

    def do_update(
        self, instance: models.Model, validated_data: dict[str, Any]
    ) -> models.Model:
        """Perform the actual model update and save."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def post_update(
        self, instance: models.Model, validated_data: dict[str, Any]
    ) -> None:
        """Hook called after do_update. Override for side effects."""

    # --- Validate lifecycle ---

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate attributes with full plugin and hook execution.

        Subclasses should not override this method. Use pre_validate/do_validate/post_validate
        hooks or plugins instead.
        """
        self._run_plugins("on_pre_validate", attrs)
        self.pre_validate(attrs)
        attrs = self.do_validate(attrs)
        self.post_validate(attrs)
        self._run_plugins("on_post_validate", attrs)
        return attrs

    def pre_validate(self, attrs: dict[str, Any]) -> None:
        """Hook called before do_validate. Override for pre-checks."""

    def do_validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Core validation logic. Override to add custom validation."""
        return attrs

    def post_validate(self, attrs: dict[str, Any]) -> None:
        """Hook called after do_validate. Override for post-checks."""

    # --- Representation ---

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Convert model instance to primitive representation."""
        representation: dict[str, Any] = super().to_representation(instance)
        return representation

    # --- Field validators ---

    def validate_slug(self, value: str) -> str:
        """Auto-generate slug from name if not provided."""
        if not value:
            return str(slugify(self.initial_data.get("name", "")))
        return value


class SoftDeletableSerializerMixin:
    """
    Mixin that handles soft-delete representation.
    """

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Add is_deleted flag and hide delete metadata for active records."""
        representation: dict[str, Any] = super().to_representation(instance)  # type: ignore[misc]
        if instance.deleted_at:
            representation["is_deleted"] = True
        else:
            representation["is_deleted"] = False
            representation.pop("deleted_at", None)
            representation.pop("deleted_by", None)
        return representation


class DefaultModelSerializer(SoftDeletableSerializerMixin, BaseSerializer):
    """
    Default serializer for most concrete model serializers.
    """

    pass
