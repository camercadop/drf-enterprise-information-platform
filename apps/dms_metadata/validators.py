"""Reusable validation utilities for DMS Metadata."""

import re
import uuid
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email

from .metadata_types import MetadataType


def validate_type(data_type: str, value: Any, label: str) -> None:
    """Validate that a value matches the structural and format requirements of a MetadataType.

    This function enforces an authoritative type schema — no implicit coercion
    or duck typing. Each MetadataType maps to exactly one valid Python/JSON
    representation:

        STRING, TEXT  — str
        INTEGER       — int (bool is rejected)
        DECIMAL       — int, float, or str castable to Decimal (bool is rejected)
        BOOLEAN       — bool only (1, 0, "true" are rejected)
        DATE          — ISO 8601 date string (YYYY-MM-DD)
        DATETIME      — ISO 8601 datetime string
        TIME          — time string (HH:MM:SS)
        UUID          — UUID string
        EMAIL         — valid email string
        URL           — valid URL string
        JSON          — dict
        ENUM          — str (choices are enforced separately by validate_rules)

    Performs isinstance checks for primitive types and format validation for
    string-based types (DATE, DATETIME, TIME, UUID, EMAIL, URL). Use `label`
    to produce context-appropriate error messages (e.g. a field code or
    "Default value").

    Args:
        data_type: The MetadataType value to validate against.
        value: The value to check. None is accepted without error.
        label: A human-readable label used in error messages.

    Raises:
        ValidationError: If the value does not match the expected type or format.

    Example:
        validate_type(MetadataType.INTEGER, 42, "Field 'quantity'")
        validate_type(MetadataType.DATE, "2025-01-01", "Default value")
    """
    if value is None:
        return

    if data_type in (MetadataType.STRING, MetadataType.TEXT, MetadataType.ENUM):
        if not isinstance(value, str):
            raise ValidationError(
                f"{label} must be a string, got {type(value).__name__}."
            )

    elif data_type == MetadataType.INTEGER:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(
                f"{label} must be an integer, got {type(value).__name__}."
            )

    elif data_type == MetadataType.DECIMAL:
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValidationError(
                f"{label} must be a decimal number, got {type(value).__name__}."
            )
        try:
            Decimal(str(value))
        except InvalidOperation as e:
            raise ValidationError(f"{label} is not a valid decimal number.") from e

    elif data_type == MetadataType.BOOLEAN:
        if not isinstance(value, bool):
            raise ValidationError(
                f"{label} must be a boolean, got {type(value).__name__}."
            )

    elif data_type == MetadataType.DATE:
        if not isinstance(value, str):
            raise ValidationError(f"{label} must be a date string (YYYY-MM-DD).")
        try:
            date.fromisoformat(value)
        except ValueError as e:
            raise ValidationError(
                f"{label} has an invalid date format. Expected YYYY-MM-DD."
            ) from e

    elif data_type == MetadataType.DATETIME:
        if not isinstance(value, str):
            raise ValidationError(f"{label} must be a datetime string (ISO 8601).")
        try:
            datetime.fromisoformat(value)
        except ValueError as e:
            raise ValidationError(
                f"{label} has an invalid datetime format. Expected ISO 8601."
            ) from e

    elif data_type == MetadataType.TIME:
        if not isinstance(value, str):
            raise ValidationError(f"{label} must be a time string (HH:MM:SS).")
        try:
            time.fromisoformat(value)
        except ValueError as e:
            raise ValidationError(
                f"{label} has an invalid time format. Expected HH:MM:SS."
            ) from e

    elif data_type == MetadataType.UUID:
        if not isinstance(value, str):
            raise ValidationError(f"{label} must be a UUID string.")
        try:
            uuid.UUID(value)
        except ValueError as e:
            raise ValidationError(f"{label} is not a valid UUID.") from e

    elif data_type == MetadataType.EMAIL:
        if not isinstance(value, str):
            raise ValidationError(f"{label} must be an email string.")
        try:
            validate_email(value)
        except ValidationError as e:
            raise ValidationError(f"{label} is not a valid email address.") from e

    elif data_type == MetadataType.URL:
        if not isinstance(value, str):
            raise ValidationError(f"{label} must be a URL string.")
        try:
            URLValidator()(value)
        except ValidationError as e:
            raise ValidationError(f"{label} is not a valid URL.") from e

    elif data_type == MetadataType.JSON:
        if not isinstance(value, dict):
            raise ValidationError(
                f"{label} must be a JSON object, got {type(value).__name__}."
            )


def validate_rules(
    data_type: str, rules: dict[str, Any], value: Any, label: str
) -> None:
    """Validate a value against the standardized validation_rules for its MetadataType.

    Applies constraints defined in `rules` (e.g. min/max, pattern, choices)
    to `value`. Use `label` to produce context-appropriate error messages.
    Skips validation if value is None.

    Args:
        data_type: The MetadataType value.
        rules: The validation_rules dict from the MetadataDefinition.
        value: The value to validate. None is accepted without error.
        label: A human-readable label used in error messages.

    Raises:
        ValidationError: If the value violates any rule.

    Example:
        validate_rules(
            MetadataType.STRING,
            {"min_length": 5, "pattern": "^[A-Z0-9-]+$"},
            "INV-001",
            "Field 'invoice_number'",
        )
        validate_rules(
            MetadataType.ENUM,
            {"choices": ["USD", "EUR", "COP"]},
            "USD",
            "Field 'currency'",
        )
    """
    if value is None:
        return

    if data_type in (MetadataType.STRING, MetadataType.TEXT):
        if "min_length" in rules and len(value) < rules["min_length"]:
            raise ValidationError(
                f"{label} must be at least {rules['min_length']} characters long."
            )
        if "max_length" in rules and len(value) > rules["max_length"]:
            raise ValidationError(
                f"{label} must be at most {rules['max_length']} characters long."
            )
        if "pattern" in rules and not re.match(rules["pattern"], value):
            raise ValidationError(f"{label} does not match the required pattern.")

    elif data_type in (MetadataType.INTEGER, MetadataType.DECIMAL):
        numeric = Decimal(str(value))
        if "min" in rules and numeric < Decimal(str(rules["min"])):
            raise ValidationError("{} must be at least {}.".format(label, rules["min"]))
        if "max" in rules and numeric > Decimal(str(rules["max"])):
            raise ValidationError("{} must be at most {}.".format(label, rules["max"]))
        if data_type == MetadataType.DECIMAL and "precision" in rules:
            if Decimal(str(value)).as_tuple().exponent < -rules["precision"]:
                raise ValidationError(
                    f"{label} must have at most {rules['precision']} decimal places."
                )

    elif data_type in (MetadataType.DATE, MetadataType.DATETIME):
        if "min" in rules and value < rules["min"]:
            raise ValidationError(
                "{} must be on or after {}.".format(label, rules["min"])
            )
        if "max" in rules and value > rules["max"]:
            raise ValidationError(
                "{} must be on or before {}.".format(label, rules["max"])
            )

    elif data_type == MetadataType.ENUM:
        choices = rules.get("choices", [])
        if value not in choices:
            raise ValidationError(
                "{} must be one of: {}.".format(label, ", ".join(choices))
            )

    elif data_type == MetadataType.URL:
        allowed_schemes = rules.get("allowed_schemes")
        if allowed_schemes:
            scheme = value.split("://")[0] if "://" in value else ""
            if scheme not in allowed_schemes:
                raise ValidationError(
                    "{} must use one of the allowed schemes: {}.".format(
                        label, ", ".join(allowed_schemes)
                    )
                )


def validate_default_value(
    data_type: str, default_value: Any, validation_rules: dict[str, Any] | None = None
) -> None:
    """Validate a default value against its data type and optional validation rules.

    Delegates to validate_type and validate_rules using "Default value" as the
    label. Called from MetadataDefinition.clean() before saving.

    Args:
        data_type: The MetadataType value.
        default_value: The value to validate. None is accepted without error.
        validation_rules: Optional rules to validate the value against.

    Raises:
        ValidationError: If the value is invalid for the type or violates a rule.

    Example:
        validate_default_value(MetadataType.INTEGER, 10)
        validate_default_value(
            MetadataType.DECIMAL, "99.99", {"min": 0, "max": 1000, "precision": 2}
        )
    """
    if default_value is None:
        return

    validate_type(data_type, default_value, "Default value")

    if validation_rules:
        validate_rules(data_type, validation_rules, default_value, "Default value")


def validate_validation_rules(data_type: str, validation_rules: dict[str, Any]) -> None:
    """Validate that validation_rules conform to the expected schema for a data type.

    Rejects rules with wrong key types or keys not valid for the given type.
    Called from MetadataDefinition.clean() to prevent storing malformed rule
    definitions. Does not validate values against the rules — use validate_rules
    for that.

    Args:
        data_type: The MetadataType value.
        validation_rules: The rules dict to validate.

    Raises:
        ValidationError: If the rules are structurally invalid for the type.

    Example:
        validate_validation_rules(
            MetadataType.STRING, {"min_length": 5, "max_length": 100}
        )
        validate_validation_rules(
            MetadataType.ENUM, {"choices": ["USD", "EUR", "COP"]}
        )
    """
    if not isinstance(validation_rules, dict):
        raise ValidationError("Validation rules must be a dictionary.")

    if data_type in (MetadataType.STRING, MetadataType.TEXT):
        if "min_length" in validation_rules and not isinstance(
            validation_rules["min_length"], int
        ):
            raise ValidationError("min_length must be an integer.")
        if "max_length" in validation_rules and not isinstance(
            validation_rules["max_length"], int
        ):
            raise ValidationError("max_length must be an integer.")
        if "pattern" in validation_rules:
            if not isinstance(validation_rules["pattern"], str):
                raise ValidationError("pattern must be a string.")
            try:
                re.compile(validation_rules["pattern"])
            except re.error as e:
                raise ValidationError(
                    "pattern is not a valid regular expression."
                ) from e

    elif data_type in (MetadataType.INTEGER, MetadataType.DECIMAL):
        if "min" in validation_rules and not isinstance(
            validation_rules["min"], (int, float)
        ):
            raise ValidationError("min must be a number.")
        if "max" in validation_rules and not isinstance(
            validation_rules["max"], (int, float)
        ):
            raise ValidationError("max must be a number.")
        if data_type == MetadataType.DECIMAL and "precision" in validation_rules:
            if (
                not isinstance(validation_rules["precision"], int)
                or validation_rules["precision"] < 0
            ):
                raise ValidationError("precision must be a non-negative integer.")

    elif data_type in (MetadataType.DATE, MetadataType.DATETIME):
        if "min" in validation_rules and not isinstance(validation_rules["min"], str):
            raise ValidationError("min must be a date string.")
        if "max" in validation_rules and not isinstance(validation_rules["max"], str):
            raise ValidationError("max must be a date string.")

    elif data_type == MetadataType.ENUM:
        if "choices" not in validation_rules:
            raise ValidationError(
                "ENUM type requires a 'choices' list in validation_rules."
            )
        if (
            not isinstance(validation_rules["choices"], list)
            or not validation_rules["choices"]
        ):
            raise ValidationError("choices must be a non-empty list.")
        if not all(isinstance(c, str) for c in validation_rules["choices"]):
            raise ValidationError("All choices must be strings.")

    elif data_type == MetadataType.URL:
        if "allowed_schemes" in validation_rules:
            if not isinstance(validation_rules["allowed_schemes"], list):
                raise ValidationError("allowed_schemes must be a list.")
            if not all(isinstance(s, str) for s in validation_rules["allowed_schemes"]):
                raise ValidationError("All allowed_schemes must be strings.")
