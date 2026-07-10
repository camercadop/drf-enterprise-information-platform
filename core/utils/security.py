"""
Security utilities.
"""

import re
import secrets
import string
from typing import Any


def validate_password_complexity(
    password: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate password complexity based on tenant-configurable rules.

    Args:
        password: The password string to validate.
        config: Optional dictionary with validation rules. Supported keys:
            min_length (int): Minimum password length. Default: 8.
            require_uppercase (bool): Require uppercase letter. Default: True.
            require_lowercase (bool): Require lowercase letter. Default: True.
            require_digits (bool): Require digit. Default: True.
            require_special (bool): Require special character. Default: True.
            forbidden_words (list[str]): Words that cannot appear in the password.

    Returns:
        A dict with ``is_valid`` (bool) and ``errors`` (list of failure messages).
    """
    if config is None:
        config = {}

    min_length = config.get("min_length", 8)
    require_uppercase = config.get("require_uppercase", True)
    require_lowercase = config.get("require_lowercase", True)
    require_digits = config.get("require_digits", True)
    require_special = config.get("require_special", True)
    forbidden_words: list[str] = config.get("forbidden_words", [])

    errors = []

    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters long.")

    if require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")

    if require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")

    if require_digits and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")

    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character.")

    for word in forbidden_words:
        if word.lower() in password.lower():
            errors.append(f"Password cannot contain the word '{word}'.")

    return {"is_valid": len(errors) == 0, "errors": errors}


def generate_api_key(length: int = 32) -> str:
    """Generate a cryptographically secure API key.

    Args:
        length: Number of characters in the generated key.

    Returns:
        A random alphanumeric string.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def mask_sensitive_data(data: str, visible_chars: int = 4, mask_char: str = "*") -> str:
    """Mask sensitive data keeping only the first and last visible characters.

    Args:
        data: The sensitive string to mask.
        visible_chars: Number of characters to keep visible at each end.
        mask_char: Single character used for masking.

    Returns:
        The masked and HTML-escaped string.

    Raises:
        ValueError: If visible_chars is negative or mask_char is not a single character.
    """
    import html

    if visible_chars < 0:
        raise ValueError("visible_chars must be non-negative.")
    if len(mask_char) != 1:
        raise ValueError("mask_char must be a single character.")

    mask_char = html.escape(mask_char)
    sanitized = html.escape(data)

    if len(sanitized) <= visible_chars:
        return mask_char * len(sanitized)

    visible_start = sanitized[:visible_chars]
    visible_end = sanitized[-visible_chars:]
    masked_length = len(sanitized) - (visible_chars * 2)
    masked = mask_char * masked_length

    return html.escape(f"{visible_start}{masked}{visible_end}")
