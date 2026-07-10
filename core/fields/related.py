"""
Custom relational fields for the enterprise platform.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class ForeignKeyField(serializers.PrimaryKeyRelatedField):
    """Foreign key field with configurable static and context-resolved filters.

    Args:
        base_filters: Static queryset filters applied unconditionally.
        context_filters: Mapping of queryset lookup keys to serializer context keys,
            resolved at validation time. Defaults to {"tenant_id": "tenant_id"}.
        exclude_deleted: Whether to filter out soft-deleted records.
        error_message: Custom "does not exist" error message.
    """

    def __init__(
        self,
        *,
        base_filters: dict[str, object] | None = None,
        context_filters: dict[str, str] | None = None,
        exclude_deleted: bool = True,
        error_message: str = "Object not found.",
        **kwargs: Any,
    ) -> None:
        self.base_filters = base_filters or {}
        self.context_filters = (
            context_filters if context_filters is not None else {"tenant_id": "tenant_id"}
        )
        self.exclude_deleted = exclude_deleted
        self.custom_error_message = error_message
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

    def fail(self, key: str, **kwargs: Any) -> None:
        if key == "does_not_exist":
            raise serializers.ValidationError(self.custom_error_message)
        super().fail(key, **kwargs)
