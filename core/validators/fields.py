"""
Django model field validators.

Deconstructible validator classes usable on model fields.
"""

import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.deconstruct import deconstructible


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
