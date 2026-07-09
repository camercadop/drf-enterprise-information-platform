"""
Custom validators for the enterprise platform.
"""

import json
import re
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.utils.deconstruct import deconstructible

# ---------------------------------------------------------------------------
# Validator classes
# ---------------------------------------------------------------------------


@deconstructible
class UsernameValidator:
    """Validate username: alphanumeric + underscores, 3-30 chars."""

    regex = re.compile(r"^[a-zA-Z0-9_]+$")
    min_length = 3
    max_length = 30

    def __call__(self, value: str) -> None:
        if not self.regex.match(value):
            raise DjangoValidationError(
                "Username can only contain letters, numbers, and underscores."
            )
        if len(value) < self.min_length:
            raise DjangoValidationError(
                f"Username must be at least {self.min_length} characters long."
            )
        if len(value) > self.max_length:
            raise DjangoValidationError(
                f"Username cannot be longer than {self.max_length} characters."
            )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UsernameValidator)


@deconstructible
class PhoneNumberValidator:
    """Validate phone number: 10-15 digits after stripping formatting."""

    min_digits = 10
    max_digits = 15

    def __call__(self, value: str) -> None:
        cleaned = re.sub(r"[\s\-\(\)\+\.]", "", value)
        if not cleaned.isdigit():
            raise DjangoValidationError("Invalid phone number format.")
        if len(cleaned) < self.min_digits or len(cleaned) > self.max_digits:
            raise DjangoValidationError(
                f"Phone number must be between {self.min_digits} and {self.max_digits} digits."
            )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PhoneNumberValidator)


@deconstructible
class EmailDomainValidator:
    """Validate that an email belongs to one of the allowed domains."""

    def __init__(self, allowed_domains: list[str]) -> None:
        self.allowed_domains = [d.lower() for d in allowed_domains]

    def __call__(self, value: str) -> None:
        if not value or "@" not in value:
            raise DjangoValidationError("Invalid email address.")

        domain = value.split("@")[1].lower()
        if domain not in self.allowed_domains:
            raise DjangoValidationError(
                f"Email domain must be one of: {', '.join(self.allowed_domains)}"
            )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, EmailDomainValidator)
            and self.allowed_domains == other.allowed_domains
        )


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def validate_email_uniqueness(
    email: str, model_class: type[models.Model], exclude_id: UUID | None = None
) -> bool:
    """Validate that an email address is unique in the database.

    Args:
        email: The email address to check.
        model_class: The Django model class to query against.
        exclude_id: Optional UUID of a record to exclude from the check.

    Returns:
        True if the email is unique, False otherwise.
    """
    queryset = model_class.objects.filter(email__iexact=email)
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)

    return not queryset.exists()


def validate_unique_slug(
    value: str,
    model_class: type[models.Model],
    field_name: str = "slug",
    exclude_id: UUID | None = None,
) -> str:
    """Validate that a slug is unique in the database.

    Args:
        value: The slug value to validate.
        model_class: The Django model class to query against.
        field_name: The model field name to check uniqueness on.
        exclude_id: Optional UUID of a record to exclude from the check.

    Returns:
        The validated slug value.

    Raises:
        DjangoValidationError: If a record with the same slug already exists.
    """
    queryset = model_class.objects.filter(**{field_name: value})
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    if queryset.exists():
        raise DjangoValidationError(
            f"A {model_class.__name__.lower()} with this {field_name} already exists."
        )

    return value


def validate_file_size(file: Any, max_size_mb: int = 10) -> bool:
    """Validate that a file size is within limits.

    Args:
        file: A file-like object with a `size` attribute.
        max_size_mb: Maximum allowed file size in megabytes.

    Returns:
        True if the file is within the size limit, False otherwise.
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    result: bool = file.size <= max_size_bytes

    return result


def validate_date_range(
    start_date: Any, end_date: Any, max_days: int = 365
) -> dict[str, Any]:
    """Validate that a date range is within acceptable limits.

    Args:
        start_date: The start date of the range.
        end_date: The end date of the range.
        max_days: Maximum number of days allowed in the range.

    Returns:
        A dict with `is_valid` (bool) and `errors` (list of strings).
    """
    errors: list[str] = []
    if start_date and end_date:
        if start_date > end_date:
            errors.append("Start date cannot be after end date.")
        if (end_date - start_date).days > max_days:
            errors.append(f"Date range cannot exceed {max_days} days.")

    return {"is_valid": len(errors) == 0, "errors": errors}


def validate_json_field(
    value: str, schema: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate a JSON field against an optional JSON schema.

    Args:
        value: A JSON string to parse and validate.
        schema: Optional JSON Schema dict to validate the parsed data against.

    Returns:
        A dict with `is_valid` (bool), `errors` (list of strings), and `data`
        (the parsed object or None on failure).
    """
    errors: list[str] = []
    try:
        data = json.loads(value)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return {"is_valid": False, "errors": errors, "data": None}

    if schema:
        import jsonschema

        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")

    return {"is_valid": len(errors) == 0, "errors": errors, "data": data}
