"""Unit tests for dms_metadata validators."""

import pytest
from django.core.exceptions import ValidationError

from apps.dms_metadata.metadata_types import MetadataType
from apps.dms_metadata.validators import (
    validate_default_value,
    validate_rules,
    validate_type,
    validate_validation_rules,
)


class TestValidateType:
    def test_string_accepts_str(self) -> None:
        validate_type(MetadataType.STRING, "hello", "Field")

    def test_string_rejects_int(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.STRING, 42, "Field")

    def test_text_accepts_str(self) -> None:
        validate_type(MetadataType.TEXT, "hello", "Field")

    def test_integer_accepts_int(self) -> None:
        validate_type(MetadataType.INTEGER, 10, "Field")

    def test_integer_rejects_bool(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.INTEGER, True, "Field")

    def test_integer_rejects_float(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.INTEGER, 1.5, "Field")

    def test_decimal_accepts_int(self) -> None:
        validate_type(MetadataType.DECIMAL, 10, "Field")

    def test_decimal_accepts_float(self) -> None:
        validate_type(MetadataType.DECIMAL, 1.5, "Field")

    def test_decimal_accepts_numeric_str(self) -> None:
        validate_type(MetadataType.DECIMAL, "99.99", "Field")

    def test_decimal_rejects_non_numeric_str(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.DECIMAL, "abc", "Field")

    def test_decimal_rejects_bool(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.DECIMAL, True, "Field")

    def test_boolean_accepts_bool(self) -> None:
        validate_type(MetadataType.BOOLEAN, True, "Field")

    def test_boolean_rejects_int(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.BOOLEAN, 1, "Field")

    def test_date_accepts_valid_iso(self) -> None:
        validate_type(MetadataType.DATE, "2025-01-01", "Field")

    def test_date_rejects_invalid_format(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.DATE, "01-01-2025", "Field")

    def test_datetime_accepts_valid_iso(self) -> None:
        validate_type(MetadataType.DATETIME, "2025-01-01T10:00:00", "Field")

    def test_datetime_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.DATETIME, "not-a-datetime", "Field")

    def test_time_accepts_valid(self) -> None:
        validate_type(MetadataType.TIME, "10:30:00", "Field")

    def test_time_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.TIME, "25:00:00", "Field")

    def test_uuid_accepts_valid(self) -> None:
        validate_type(MetadataType.UUID, "12345678-1234-5678-1234-567812345678", "Field")

    def test_uuid_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.UUID, "not-a-uuid", "Field")

    def test_email_accepts_valid(self) -> None:
        validate_type(MetadataType.EMAIL, "user@example.com", "Field")

    def test_email_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.EMAIL, "not-an-email", "Field")

    def test_url_accepts_valid(self) -> None:
        validate_type(MetadataType.URL, "https://example.com", "Field")

    def test_url_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.URL, "not-a-url", "Field")

    def test_json_accepts_dict(self) -> None:
        validate_type(MetadataType.JSON, {"key": "value"}, "Field")

    def test_json_rejects_list(self) -> None:
        with pytest.raises(ValidationError):
            validate_type(MetadataType.JSON, [1, 2], "Field")

    def test_enum_accepts_str(self) -> None:
        validate_type(MetadataType.ENUM, "USD", "Field")

    def test_none_is_always_accepted(self) -> None:
        for data_type in MetadataType:
            validate_type(data_type, None, "Field")


class TestValidateRules:
    def test_string_min_length_passes(self) -> None:
        validate_rules(MetadataType.STRING, {"min_length": 3}, "hello", "Field")

    def test_string_min_length_fails(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(MetadataType.STRING, {"min_length": 10}, "hi", "Field")

    def test_string_max_length_passes(self) -> None:
        validate_rules(MetadataType.STRING, {"max_length": 10}, "hello", "Field")

    def test_string_max_length_fails(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(MetadataType.STRING, {"max_length": 3}, "hello", "Field")

    def test_string_pattern_passes(self) -> None:
        validate_rules(MetadataType.STRING, {"pattern": r"^[A-Z]+"}, "HELLO", "Field")

    def test_string_pattern_fails(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(MetadataType.STRING, {"pattern": r"^[A-Z]+"}, "hello", "Field")

    def test_integer_min_passes(self) -> None:
        validate_rules(MetadataType.INTEGER, {"min": 0}, 5, "Field")

    def test_integer_min_fails(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(MetadataType.INTEGER, {"min": 10}, 5, "Field")

    def test_integer_max_passes(self) -> None:
        validate_rules(MetadataType.INTEGER, {"max": 100}, 50, "Field")

    def test_integer_max_fails(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(MetadataType.INTEGER, {"max": 10}, 50, "Field")

    def test_decimal_precision_passes(self) -> None:
        validate_rules(MetadataType.DECIMAL, {"precision": 2}, "99.99", "Field")

    def test_decimal_precision_fails(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(MetadataType.DECIMAL, {"precision": 1}, "99.99", "Field")

    def test_enum_valid_choice(self) -> None:
        validate_rules(MetadataType.ENUM, {"choices": ["USD", "EUR"]}, "USD", "Field")

    def test_enum_invalid_choice(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(MetadataType.ENUM, {"choices": ["USD", "EUR"]}, "COP", "Field")

    def test_url_allowed_scheme_passes(self) -> None:
        validate_rules(
            MetadataType.URL, {"allowed_schemes": ["https"]}, "https://example.com", "Field"
        )

    def test_url_disallowed_scheme_fails(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(
                MetadataType.URL, {"allowed_schemes": ["https"]}, "http://example.com", "Field"
            )

    def test_date_min_passes(self) -> None:
        validate_rules(MetadataType.DATE, {"min": "2020-01-01"}, "2025-01-01", "Field")

    def test_date_min_fails(self) -> None:
        with pytest.raises(ValidationError):
            validate_rules(MetadataType.DATE, {"min": "2026-01-01"}, "2025-01-01", "Field")

    def test_none_is_always_skipped(self) -> None:
        validate_rules(MetadataType.STRING, {"min_length": 100}, None, "Field")


class TestValidateValidationRules:
    def test_string_valid_rules(self) -> None:
        validate_validation_rules(MetadataType.STRING, {"min_length": 1, "max_length": 100})

    def test_string_invalid_min_length_type(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.STRING, {"min_length": "five"})

    def test_string_invalid_pattern(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.STRING, {"pattern": "["})

    def test_integer_valid_rules(self) -> None:
        validate_validation_rules(MetadataType.INTEGER, {"min": 0, "max": 100})

    def test_integer_invalid_min_type(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.INTEGER, {"min": "zero"})

    def test_decimal_valid_precision(self) -> None:
        validate_validation_rules(MetadataType.DECIMAL, {"precision": 2})

    def test_decimal_negative_precision(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.DECIMAL, {"precision": -1})

    def test_enum_requires_choices(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.ENUM, {})

    def test_enum_empty_choices(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.ENUM, {"choices": []})

    def test_enum_non_string_choices(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.ENUM, {"choices": [1, 2]})

    def test_enum_valid_choices(self) -> None:
        validate_validation_rules(MetadataType.ENUM, {"choices": ["A", "B"]})

    def test_url_valid_allowed_schemes(self) -> None:
        validate_validation_rules(MetadataType.URL, {"allowed_schemes": ["https"]})

    def test_url_invalid_allowed_schemes_type(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.URL, {"allowed_schemes": "https"})

    def test_not_a_dict_raises(self) -> None:
        with pytest.raises(ValidationError):
            validate_validation_rules(MetadataType.STRING, "not-a-dict")  # type: ignore[arg-type]


class TestValidateDefaultValue:
    def test_valid_type_and_rules(self) -> None:
        validate_default_value(MetadataType.INTEGER, 5, {"min": 0, "max": 10})

    def test_invalid_type(self) -> None:
        with pytest.raises(ValidationError):
            validate_default_value(MetadataType.INTEGER, "five")

    def test_violates_rules(self) -> None:
        with pytest.raises(ValidationError):
            validate_default_value(MetadataType.INTEGER, 50, {"max": 10})

    def test_none_is_accepted(self) -> None:
        validate_default_value(MetadataType.INTEGER, None)
