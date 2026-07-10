import pytest

from core.utils.security import (
    generate_api_key,
    mask_sensitive_data,
    validate_password_complexity,
)


class TestValidatePasswordComplexity:
    def test_valid_password_with_defaults(self) -> None:
        result = validate_password_complexity("Str0ng!Pass")
        assert result["is_valid"] is True
        assert result["errors"] == []

    def test_too_short(self) -> None:
        result = validate_password_complexity("Ab1!")
        assert result["is_valid"] is False
        assert any("at least 8" in e for e in result["errors"])

    def test_missing_uppercase(self) -> None:
        result = validate_password_complexity("lowercase1!")
        assert result["is_valid"] is False
        assert any("uppercase" in e for e in result["errors"])

    def test_missing_lowercase(self) -> None:
        result = validate_password_complexity("UPPERCASE1!")
        assert result["is_valid"] is False
        assert any("lowercase" in e for e in result["errors"])

    def test_missing_digit(self) -> None:
        result = validate_password_complexity("NoDigits!!")
        assert result["is_valid"] is False
        assert any("digit" in e for e in result["errors"])

    def test_missing_special(self) -> None:
        result = validate_password_complexity("NoSpecial1A")
        assert result["is_valid"] is False
        assert any("special" in e for e in result["errors"])

    def test_forbidden_words(self) -> None:
        config = {"forbidden_words": ["password"]}
        result = validate_password_complexity("Password1!", config)
        assert result["is_valid"] is False
        assert any("password" in e for e in result["errors"])

    def test_custom_min_length(self) -> None:
        config = {"min_length": 12}
        result = validate_password_complexity("Short1!a", config)
        assert result["is_valid"] is False

    def test_disabled_requirements(self) -> None:
        config = {
            "require_uppercase": False,
            "require_lowercase": False,
            "require_digits": False,
            "require_special": False,
            "min_length": 1,
        }
        result = validate_password_complexity("a", config)
        assert result["is_valid"] is True


class TestGenerateApiKey:
    def test_default_length(self) -> None:
        key = generate_api_key()
        assert len(key) == 32

    def test_custom_length(self) -> None:
        key = generate_api_key(length=64)
        assert len(key) == 64

    def test_alphanumeric_only(self) -> None:
        key = generate_api_key()
        assert key.isalnum()

    def test_uniqueness(self) -> None:
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100


class TestMaskSensitiveData:
    def test_basic_masking(self) -> None:
        result = mask_sensitive_data("1234567890")
        assert result.startswith("1234")
        assert result.endswith("7890")
        assert "*" in result

    def test_short_string(self) -> None:
        result = mask_sensitive_data("ab", visible_chars=4)
        assert result == "**"

    def test_custom_mask_char(self) -> None:
        result = mask_sensitive_data("1234567890", mask_char="X")
        assert "X" in result

    def test_negative_visible_chars_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            mask_sensitive_data("test", visible_chars=-1)

    def test_invalid_mask_char_raises(self) -> None:
        with pytest.raises(ValueError, match="single character"):
            mask_sensitive_data("test", mask_char="XX")
