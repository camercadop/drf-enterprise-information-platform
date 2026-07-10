import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from core.utils.validators import (
    EmailDomainValidator,
    PhoneNumberValidator,
    UsernameValidator,
    validate_date_range,
    validate_file_size,
    validate_json_field,
)


class TestUsernameValidator:
    def setup_method(self) -> None:
        self.validator = UsernameValidator()

    def test_valid_username(self) -> None:
        self.validator("valid_user123")

    def test_too_short(self) -> None:
        with pytest.raises(DjangoValidationError, match="at least 3"):
            self.validator("ab")

    def test_too_long(self) -> None:
        with pytest.raises(DjangoValidationError, match="cannot be longer"):
            self.validator("a" * 31)

    def test_invalid_characters(self) -> None:
        with pytest.raises(DjangoValidationError, match="letters, numbers, and underscores"):
            self.validator("user@name")

    def test_equality(self) -> None:
        assert UsernameValidator() == UsernameValidator()


class TestPhoneNumberValidator:
    def setup_method(self) -> None:
        self.validator = PhoneNumberValidator()

    def test_valid_phone(self) -> None:
        self.validator("+1 (555) 123-4567")

    def test_valid_plain_digits(self) -> None:
        self.validator("5551234567")

    def test_too_few_digits(self) -> None:
        with pytest.raises(DjangoValidationError, match="between"):
            self.validator("12345")

    def test_too_many_digits(self) -> None:
        with pytest.raises(DjangoValidationError, match="between"):
            self.validator("1" * 16)

    def test_non_numeric(self) -> None:
        with pytest.raises(DjangoValidationError, match="Invalid"):
            self.validator("abcdefghij")


class TestEmailDomainValidator:
    def setup_method(self) -> None:
        self.validator = EmailDomainValidator(["example.com", "corp.io"])

    def test_valid_domain(self) -> None:
        self.validator("user@example.com")

    def test_invalid_domain(self) -> None:
        with pytest.raises(DjangoValidationError, match="must be one of"):
            self.validator("user@other.com")

    def test_no_at_sign(self) -> None:
        with pytest.raises(DjangoValidationError, match="Invalid email"):
            self.validator("invalid")

    def test_case_insensitive(self) -> None:
        self.validator("user@EXAMPLE.COM")

    def test_equality(self) -> None:
        a = EmailDomainValidator(["example.com"])
        b = EmailDomainValidator(["example.com"])
        assert a == b


class TestValidateFileSize:
    def test_within_limit(self) -> None:
        class FakeFile:
            size = 5 * 1024 * 1024

        assert validate_file_size(FakeFile(), max_size_mb=10) is True

    def test_exceeds_limit(self) -> None:
        class FakeFile:
            size = 15 * 1024 * 1024

        assert validate_file_size(FakeFile(), max_size_mb=10) is False


class TestValidateDateRange:
    def test_valid_range(self) -> None:
        from datetime import date

        result = validate_date_range(date(2024, 1, 1), date(2024, 6, 1))
        assert result["is_valid"] is True

    def test_start_after_end(self) -> None:
        from datetime import date

        result = validate_date_range(date(2024, 6, 1), date(2024, 1, 1))
        assert result["is_valid"] is False
        assert any("after" in e for e in result["errors"])

    def test_exceeds_max_days(self) -> None:
        from datetime import date

        result = validate_date_range(date(2024, 1, 1), date(2026, 1, 1), max_days=365)
        assert result["is_valid"] is False
        assert any("exceed" in e for e in result["errors"])


class TestValidateJsonField:
    def test_valid_json(self) -> None:
        result = validate_json_field('{"key": "value"}')
        assert result["is_valid"] is True
        assert result["data"] == {"key": "value"}

    def test_invalid_json(self) -> None:
        result = validate_json_field("not json")
        assert result["is_valid"] is False
        assert result["data"] is None

    def test_schema_validation_pass(self) -> None:
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = validate_json_field('{"name": "test"}', schema=schema)
        assert result["is_valid"] is True

    def test_schema_validation_fail(self) -> None:
        schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
        result = validate_json_field('{}', schema=schema)
        assert result["is_valid"] is False
