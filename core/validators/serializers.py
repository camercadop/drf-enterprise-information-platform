"""
DRF serializer-level validators.

Validators that plug into serializer Meta.validators for cross-field validation.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class UniqueTogetherContextValidator:
    """Validates uniqueness using a combination of field values and context values.

    Args:
        fields: Mapping of queryset lookup keys to serializer field names.
        context_fields: Mapping of queryset lookup keys to serializer context keys.
            Defaults to {"tenant_id": "tenant_id"}.
        queryset: Explicit queryset. If not provided, inferred from serializer's Meta.model.
        message: Error message on violation.
    """

    requires_context = True

    def __init__(
        self,
        *,
        fields: dict[str, str],
        context_fields: dict[str, str] | None = None,
        queryset: Any | None = None,
        message: str = "This combination already exists.",
    ) -> None:
        self.fields = fields
        self.context_fields = (
            context_fields if context_fields is not None else {"tenant_id": "tenant_id"}
        )
        self.queryset = queryset
        self.message = message

    def __call__(self, attrs: dict[str, Any], serializer: Any) -> None:
        qs = self.queryset
        if qs is None:
            qs = serializer.Meta.model.objects.all()

        assert qs is not None, (
            "UniqueTogetherContextValidator requires either an explicit queryset "
            "or a Meta.model on the serializer."
        )

        filters = {
            lookup: attrs[field_name] for lookup, field_name in self.fields.items()
        }
        for lookup, context_key in self.context_fields.items():
            filters[lookup] = serializer.context[context_key]

        if qs.filter(**filters).exists():
            raise serializers.ValidationError(self.message)
