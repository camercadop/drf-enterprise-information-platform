"""Serializers for DMS Metadata."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.base.serializers import DefaultModelSerializer

from .models import MetadataDefinition
from .validators import validate_default_value, validate_validation_rules


class MetadataDefinitionSerializer(DefaultModelSerializer):
    """Serializer for MetadataDefinition create and update operations.

    Validates validation_rules structure against data_type, and default_value
    against both data_type and validation_rules when present. document_type is
    injected by the nested viewset via pre_create — it is not a writable field.
    """

    class Meta:
        model = MetadataDefinition
        fields = [
            "id",
            "document_type",
            "code",
            "name",
            "data_type",
            "required",
            "searchable",
            "filterable",
            "sortable",
            "indexed",
            "default_value",
            "validation_rules",
            "created_at",
            "updated_at",
        ]

    def do_validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate validation_rules structure and default_value against data_type.

        Runs cross-field validation that requires both data_type and the JSON
        fields to be present. Delegates to the reusable validator functions in
        validators.py.

        Args:
            attrs: The validated field values.

        Returns:
            The unchanged attrs dict if validation passes.

        Raises:
            serializers.ValidationError: If validation_rules or default_value
                are invalid for the given data_type.
        """
        data_type = attrs.get("data_type")
        validation_rules = attrs.get("validation_rules")
        default_value = attrs.get("default_value")

        if data_type and validation_rules is not None:
            try:
                validate_validation_rules(data_type, validation_rules)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"validation_rules": e.message}) from e

        if data_type and default_value is not None:
            try:
                validate_default_value(data_type, default_value, validation_rules)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"default_value": e.message}) from e

        return attrs
