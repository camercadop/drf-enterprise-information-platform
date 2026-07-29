from django.conf import settings

DEFAULTS: dict[str, object] = {
    "AUTHORIZATION_CODE_LIFETIME": 600,
    "ACCESS_TOKEN_LIFETIME_MINUTES": 30,
    "REFRESH_TOKEN_LIFETIME_DAYS": 7,
    "PKCE_REQUIRED_FOR_PUBLIC_CLIENTS": True,
    "SUPPORTED_GRANT_TYPES": [
        "authorization_code",
        "client_credentials",
        "refresh_token",
    ],
    "SUPPORTED_RESPONSE_TYPES": ["code"],
    "TOKEN_FORMAT": "JWT",
}


def get_oauth2_setting(key: str) -> object:
    """Get an OAuth2 setting value, with project-level override support.

    Reads from the OAUTH2 dict in Django settings if present, falling back
    to the defaults defined in this module. Raises KeyError for unknown keys.

    Args:
        key: The setting key to look up.

    Returns:
        The resolved setting value.

    Raises:
        KeyError: If the key is not a known OAuth2 setting.
    """
    user_settings: dict[str, object] = getattr(settings, "OAUTH2", {})
    if key not in DEFAULTS:
        raise KeyError(f"Unknown OAuth2 setting: {key!r}")
    return user_settings.get(key, DEFAULTS[key])
