"""Custom relational fields for the enterprise platform."""

import logging
from typing import Any

from rest_framework import serializers

logger = logging.getLogger(__name__)


class ForeignKeyField(serializers.PrimaryKeyRelatedField):
    """Foreign key field with configurable static and context-resolved filters.

    Args:
        base_filters: Static queryset filters applied unconditionally.
        context_filters: Mapping of queryset lookup keys to serializer context keys,
            resolved at validation time. Defaults to {"tenant_id": "tenant_id"}.
        exclude_deleted: Whether to filter out soft-deleted records.
        error_message: Custom "does not exist" error message.
        representation_fields: Fields to include in the nested output. Supports ``__``
            traversal. Takes precedence over the model's ``fk_representation_fields``.
    """

    def __init__(
        self,
        *,
        base_filters: dict[str, object] | None = None,
        context_filters: dict[str, str] | None = None,
        exclude_deleted: bool = True,
        error_message: str = "Object not found.",
        representation_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.base_filters = base_filters or {}
        self.context_filters = (
            context_filters if context_filters is not None else {"tenant_id": "tenant_id"}
        )
        self.exclude_deleted = exclude_deleted
        self.custom_error_message = error_message
        self.representation_fields = representation_fields
        super().__init__(**kwargs)

    def get_queryset(self) -> Any:
        queryset = super().get_queryset()

        if self.exclude_deleted:
            queryset = queryset.filter(deleted_at__isnull=True)

        if self.base_filters:
            queryset = queryset.filter(**self.base_filters)

        if self.context_filters:
            resolved = {
                lookup: self.context[context_key]
                for lookup, context_key in self.context_filters.items()
            }
            queryset = queryset.filter(**resolved)

        return queryset

    def _represent_instance(
        self,
        instance: Any,
        fields: list[str] | None,
        visited: set[tuple[type, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build a dict representation for a model instance given an explicit field list.

        If ``fields`` is None, falls back to ``{"id": str(instance.pk), "label": str(instance)}``.
        If a resolved value is itself a model instance, it is represented recursively
        using its own ``fk_representation_fields`` class attribute (or the fallback).
        Circular references are detected via ``visited`` and fall back to the id/label
        representation with a warning log.

        Args:
            instance: The model instance to represent.
            fields: The list of field names to include, or None to use the fallback.
            visited: Set of (class, pk) pairs already seen in the current recursion chain.

        Returns:
            A dict representation of the instance.
        """
        from django.db.models import Model, QuerySet

        if visited is None:
            visited = set()

        if hasattr(instance, "pk"):
            identity = (instance.__class__, instance.pk)
            if identity in visited:
                logger.warning(
                    "ForeignKeyField: circular reference detected for %s pk=%s, using fallback",
                    instance.__class__.__name__,
                    instance.pk,
                )
                return {"id": str(instance.pk), "label": str(instance)}
            visited = visited | {identity}

        if fields is None:
            return {"id": str(instance.pk), "label": str(instance)}

        result: dict[str, Any] = {}
        for field_name in fields:
            value = self._resolve_field_value(field_name, instance, self.parent)
            if isinstance(value, Model):
                nested_fields: list[str] | None = getattr(
                    value.__class__, "fk_representation_fields", None
                )
                value = self._represent_instance(value, nested_fields, visited)
            elif isinstance(value, (QuerySet, list)):
                value = [
                    self._represent_instance(
                        item,
                        getattr(item.__class__, "fk_representation_fields", None),
                        visited,
                    )
                    if isinstance(item, Model)
                    else item
                    for item in value
                ]
            result[field_name] = value
        return result

    def _resolve_field_value(self, field_name: str, instance: Any, serializer: Any | None = None) -> Any:
        """Resolve the value for a single field name against an instance.

        Resolution order:
            1. Serializer hook ``get_<field_name>_representation(instance)`` (root level only).
            2. Model instance hook ``get_<field_name>_representation()`` on the current instance.
            3. Dotted traversal via ``__``: at each level, tries ``get_<segment>()`` on the
               current instance before falling back to ``getattr``, then recurses with the
               remaining path applying the same hook cascade
               (e.g. ``role__name__suffix`` tries ``get_role__name__suffix_representation()`` on
               root, then ``get_name__suffix_representation()`` on ``role``, then
               ``get_suffix_representation()`` on ``name``, then ``getattr(name, "suffix")``)
            4. Direct ``getattr`` on the instance.
            5. Returns None with a warning log if nothing resolves.

        Args:
            field_name: The field name to resolve, supports ``__`` for traversal.
            instance: The model instance being serialized.
            serializer: The parent serializer, used to look up serializer-level hooks.
                Only consulted at the root call level.

        Returns:
            The resolved value, or None if unresolvable.
        """
        if serializer is not None:
            serializer_hook = f"get_{field_name}_representation"
            if hasattr(serializer, serializer_hook):
                return getattr(serializer, serializer_hook)(instance)

        model_hook = f"get_{field_name}_representation"
        if hasattr(instance, model_hook):
            return getattr(instance, model_hook)()

        if "__" in field_name:
            head, tail = field_name.split("__", 1)
            traversal_hook = f"get_{head}"
            if hasattr(instance, traversal_hook):
                next_instance = getattr(instance, traversal_hook)()
            else:
                next_instance = getattr(instance, head, None)
            if next_instance is None:
                logger.warning(
                    "ForeignKeyField: traversal failed at '%s' for field '%s' on %s",
                    head,
                    field_name,
                    instance.__class__.__name__,
                )
                return None
            return self._resolve_field_value(tail, next_instance)

        if not hasattr(instance, field_name):
            logger.warning(
                "ForeignKeyField: field '%s' not found on %s",
                field_name,
                instance.__class__.__name__,
            )
            return None

        return getattr(instance, field_name)

    def to_representation(self, value: Any) -> Any:
        """Serialize the related instance as a nested object.

        Resolves the field list from the field-level ``representation_fields`` param,
        then the model's ``fk_representation_fields`` class attribute, then falls back
        to ``{"id": str(value.pk), "label": str(value)}``.

        Args:
            value: The related model instance.

        Returns:
            A dict representation of the instance.
        """
        fields = self.representation_fields or getattr(
            value.__class__, "fk_representation_fields", None
        )
        return self._represent_instance(value, fields)

    def fail(self, key: str, **kwargs: Any) -> None:
        if key == "does_not_exist":
            raise serializers.ValidationError(self.custom_error_message)
        super().fail(key, **kwargs)
