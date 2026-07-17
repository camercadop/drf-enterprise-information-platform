"""Rate limiting for the login endpoint.

Two independent throttles are applied to ``LoginView``:

- ``LoginIPThrottle`` — scoped to the client IP address.
- ``LoginEmailThrottle`` — scoped to the email submitted in the request body.

Both use the default Redis cache. Rates are read from ``settings.AUTH_RATE_LIMIT``
and fall back to ``10/minute`` (IP) and ``5/minute`` (email) when not configured.
"""

from django.conf import settings
from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle


def _rate(key: str, default: str) -> str | None:
    """Return the configured rate for the given key from AUTH_RATE_LIMIT settings.

    Args:
        key: The settings key to look up (e.g. ``IP_RATE``).
        default: Fallback rate string if the key is absent.

    Returns:
        A DRF rate string such as ``'10/minute'``, or ``None`` if the value is ``'0'``
        (which disables throttling for that scope).
    """
    config: dict[str, str] = getattr(settings, "AUTH_RATE_LIMIT", {})
    value = str(config.get(key, default))
    return None if value == "0" else value


class LoginIPThrottle(SimpleRateThrottle):
    """Throttle login attempts by client IP address.

    Keyed on the resolved client IP. Rate is read from
    ``settings.AUTH_RATE_LIMIT['IP_RATE']``, defaulting to ``10/minute``.
    """

    scope = "login_ip"

    def get_rate(self) -> str | None:
        """Return the configured IP rate limit, or ``None`` to disable throttling."""
        return _rate("IP_RATE", "10/minute")

    def get_cache_key(self, request: Request, view: object) -> str:
        """Return the cache key scoped to the client IP.

        Args:
            request: The incoming DRF request.
            view: The view being throttled (unused).

        Returns:
            A cache key string unique to the client IP.
        """
        ident = self.get_ident(request)
        return str(self.cache_format % {"scope": self.scope, "ident": ident})


class LoginEmailThrottle(SimpleRateThrottle):
    """Throttle login attempts by submitted email address.

    Keyed on the lowercased email from the request body. Rate is read from
    ``settings.AUTH_RATE_LIMIT['EMAIL_RATE']``, defaulting to ``5/minute``.
    Falls back to IP-based key if no email is present.
    """

    scope = "login_email"

    def get_rate(self) -> str | None:
        """Return the configured email rate limit, or ``None`` to disable throttling."""
        return _rate("EMAIL_RATE", "5/minute")

    def get_cache_key(self, request: Request, view: object) -> str:
        """Return the cache key scoped to the submitted email address.

        Args:
            request: The incoming DRF request.
            view: The view being throttled (unused).

        Returns:
            A cache key string unique to the email, or IP if email is absent.
        """
        email: str = (
            request.data.get("email", "") if isinstance(request.data, dict) else ""
        )
        ident = email.lower() if email else self.get_ident(request)
        return str(self.cache_format % {"scope": self.scope, "ident": ident})
