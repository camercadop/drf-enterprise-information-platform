"""Unit tests for MetadataValidationService."""

import pytest
from django.core.exceptions import ValidationError
from unittest.mock import MagicMock, patch

from apps.dms_metadata.metadata_types import MetadataType
from apps.dms_metadata.services import MetadataValidationService


def _make_definition(code: str, data_type: str, required: bool = False, validation_rules=None):
    """Build a mock MetadataDefinition."""
    d = MagicMock()
    d.code = code
    d.name = code.replace("_", " ").title()
    d.data_type = data_type
    d.required = required
    d.validation_rules = validation_rules
    return d


class TestMetadataValidationServiceValidate:
    def _run(self, definitions, metadata):
        doc_type = MagicMock()
        with patch(
            "apps.dms_metadata.services.MetadataDefinition.objects.filter",
            return_value=definitions,
        ):
            MetadataValidationService.validate(doc_type, metadata)

    def test_valid_metadata_passes(self) -> None:
        defs = [_make_definition("amount", MetadataType.INTEGER)]
        self._run(defs, {"amount": 100})

    def test_missing_required_field_raises(self) -> None:
        defs = [_make_definition("amount", MetadataType.INTEGER, required=True)]
        with pytest.raises(ValidationError, match="amount"):
            self._run(defs, {})

    def test_missing_optional_field_passes(self) -> None:
        defs = [_make_definition("amount", MetadataType.INTEGER, required=False)]
        self._run(defs, {})

    def test_wrong_type_raises(self) -> None:
        defs = [_make_definition("amount", MetadataType.INTEGER)]
        with pytest.raises(ValidationError):
            self._run(defs, {"amount": "not-an-int"})

    def test_extra_field_raises(self) -> None:
        defs = [_make_definition("amount", MetadataType.INTEGER)]
        with pytest.raises(ValidationError, match="undefined"):
            self._run(defs, {"amount": 10, "unknown_field": "x"})

    def test_empty_metadata_with_no_definitions_passes(self) -> None:
        self._run([], {})

    def test_validation_rules_applied(self) -> None:
        defs = [
            _make_definition(
                "amount", MetadataType.INTEGER, validation_rules={"min": 0, "max": 10}
            )
        ]
        with pytest.raises(ValidationError):
            self._run(defs, {"amount": 999})

    def test_validation_rules_pass_when_satisfied(self) -> None:
        defs = [
            _make_definition(
                "amount", MetadataType.INTEGER, validation_rules={"min": 0, "max": 10}
            )
        ]
        self._run(defs, {"amount": 5})

    def test_enum_valid_choice(self) -> None:
        defs = [
            _make_definition(
                "currency", MetadataType.ENUM, validation_rules={"choices": ["USD", "EUR"]}
            )
        ]
        self._run(defs, {"currency": "USD"})

    def test_enum_invalid_choice_raises(self) -> None:
        defs = [
            _make_definition(
                "currency", MetadataType.ENUM, validation_rules={"choices": ["USD", "EUR"]}
            )
        ]
        with pytest.raises(ValidationError):
            self._run(defs, {"currency": "COP"})
