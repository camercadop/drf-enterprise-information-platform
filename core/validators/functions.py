"""
Standalone validation utility functions.

Reusable validation logic for uniqueness checks, file size, date ranges, and JSON parsing.
"""

import json
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models


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
