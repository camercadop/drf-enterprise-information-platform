"""
Base serializers for the enterprise platform.
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils.text import slugify
from rest_framework import serializers


class SerializerPlugin:
    """
    Base class for serializer plugins.

    Plugins are stateless and participate in the serializer lifecycle.
    They receive the serializer instance as first argument (which gives access to context/request).
    Short-circuit by raising any exception.

    Available hooks:
        on_pre_create(serializer, validated_data)
        on_post_create(serializer, instance)
        on_pre_update(serializer, instance, validated_data)
        on_post_update(serializer, instance)
        on_pre_validate(serializer, data)
        on_post_validate(serializer, validated_data)
    """


class BaseSerializer(serializers.ModelSerializer):
    """
    Base serializer with plugin system and template method lifecycle.
    """

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        abstract = True
        extensions: list[type[SerializerPlugin]] = []

    # --- Plugin dispatch ---

    def _get_plugins(self) -> list[SerializerPlugin]:
        extensions: list[type[SerializerPlugin]] = getattr(self.Meta, "extensions", [])
        return [plugin() for plugin in extensions]

    def _run_plugins(self, hook: str, *args: Any, **kwargs: Any) -> None:
        for plugin in self._get_plugins():
            if hasattr(plugin, hook):
                getattr(plugin, hook)(self, *args, **kwargs)



    # --- Create lifecycle ---

    def create(self, validated_data: dict[str, Any]) -> models.Model:
        self._run_plugins("on_pre_create", validated_data)
        self.pre_create(validated_data)
        instance = self.do_create(validated_data)
        self.post_create(instance, validated_data)
        self._run_plugins("on_post_create", instance)
        return instance

    def pre_create(self, validated_data: dict[str, Any]) -> None:
        pass

    def do_create(self, validated_data: dict[str, Any]) -> models.Model:
        instance = self.Meta.model(**validated_data)  # type: ignore[attr-defined]
        instance.save()
        return instance

    def post_create(self, instance: models.Model, validated_data: dict[str, Any]) -> None:
        pass

    # --- Update lifecycle ---

    def update(self, instance: models.Model, validated_data: dict[str, Any]) -> models.Model:
        self._run_plugins("on_pre_update", instance, validated_data)
        self.pre_update(instance, validated_data)
        instance = self.do_update(instance, validated_data)
        self.post_update(instance, validated_data)
        self._run_plugins("on_post_update", instance)
        return instance

    def pre_update(self, instance: models.Model, validated_data: dict[str, Any]) -> None:
        pass

    def do_update(self, instance: models.Model, validated_data: dict[str, Any]) -> models.Model:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def post_update(self, instance: models.Model, validated_data: dict[str, Any]) -> None:
        pass

    # --- Validate lifecycle ---

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        self._run_plugins("on_pre_validate", attrs)
        self.pre_validate(attrs)
        attrs = self.do_validate(attrs)
        self.post_validate(attrs)
        self._run_plugins("on_post_validate", attrs)
        return attrs

    def pre_validate(self, attrs: dict[str, Any]) -> None:
        pass

    def do_validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        return attrs

    def post_validate(self, attrs: dict[str, Any]) -> None:
        pass

    # --- Representation ---

    def to_representation(self, instance: Any) -> dict[str, Any]:
        representation: dict[str, Any] = super().to_representation(instance)
        return representation

    # --- Field validators ---

    def validate_slug(self, value: str) -> str:
        if not value:
            return str(slugify(self.initial_data.get("name", "")))
        return value


class SoftDeletableSerializerMixin:
    """
    Mixin that handles soft-delete representation.
    """

    def to_representation(self, instance: Any) -> dict[str, Any]:
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
