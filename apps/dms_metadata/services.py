"""Services for DMS Metadata."""

from typing import Any

from django.core.exceptions import ValidationError

from apps.dms_document_types.models import DocumentType
from apps.dms_metadata.models import MetadataDefinition
from apps.dms_metadata.validators import validate_rules, validate_type


class MetadataValidationService:
    """Validates document metadata against MetadataDefinition rules for a document type.

    Use this service as the single validation entry point from serializers,
    management commands, background jobs, and imports. Do not duplicate
    validation logic elsewhere.
    """

    @staticmethod
    def validate(document_type: DocumentType, metadata: dict[str, Any]) -> None:
        """Validate metadata values against all definitions for a document type.

        Checks required fields, data types, validation rules, and rejects
        keys not declared in any MetadataDefinition for the given type.

        Args:
            document_type: The document type whose definitions are used.
            metadata: The metadata dict to validate.

        Raises:
            ValidationError: If any field is missing, has the wrong type,
                violates a rule, or is not declared in the definitions.

        Example:
            MetadataValidationService.validate(
                document_type=invoice_type,
                metadata={"invoice_number": "INV-001", "amount": "1500.00"},
            )
        """
        definitions = MetadataDefinition.objects.filter(document_type=document_type)

        for definition in definitions:
            MetadataValidationService._validate_definition(definition, metadata)

        MetadataValidationService._validate_no_extra_fields(metadata, definitions)

    @staticmethod
    def _validate_definition(
        definition: MetadataDefinition, metadata: dict[str, Any]
    ) -> None:
        """Validate a single definition against the provided metadata dict.

        Args:
            definition: The definition to validate against.
            metadata: The full metadata dict.

        Raises:
            ValidationError: If the field is missing (and required), has the
                wrong type, or violates the definition's validation rules.
        """
        code = definition.code

        if code not in metadata:
            if definition.required:
                raise ValidationError(
                    f"Required metadata field '{code}' ({definition.name}) is missing."
                )
            return

        value = metadata[code]
        validate_type(definition.data_type, value, f"Field '{code}'")

        if definition.validation_rules:
            validate_rules(
                definition.data_type, definition.validation_rules, value, f"Field '{code}'"
            )

    @staticmethod
    def _validate_no_extra_fields(
        metadata: dict[str, Any], definitions: Any
    ) -> None:
        """Reject metadata keys that have no corresponding MetadataDefinition.

        Args:
            metadata: The metadata dict to check.
            definitions: QuerySet of MetadataDefinition for the document type.

        Raises:
            ValidationError: If any key in metadata is not declared in definitions.
        """
        defined_codes = {d.code for d in definitions}
        extra = set(metadata.keys()) - defined_codes
        if extra:
            raise ValidationError(
                "Metadata contains undefined fields: {}.".format(", ".join(sorted(extra)))
            )
