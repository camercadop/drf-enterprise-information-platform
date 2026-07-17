"""Account lockout service backed by Redis.

Uses two keys per email:
- ``auth:lockout:attempts:{email}`` — failed attempt counter, expires after lockout window
- ``auth:lockout:locked:{email}`` — lockout flag, TTL drives auto-unlock

Global defaults are read from ``settings.AUTH_LOCKOUT``. A ``LOCKOUT_DURATION``
of 0 means the account stays locked until manually unlocked via the admin endpoint.
"""

from django.conf import settings
from django.core.cache import cache

_ATTEMPTS_KEY = "auth:lockout:attempts:{email}"
_LOCKED_KEY = "auth:lockout:locked:{email}"

_DEFAULT_MAX_ATTEMPTS = 5
_DEFAULT_LOCKOUT_DURATION = 900  # seconds


def _config() -> dict[str, int]:
    """Return the active lockout configuration from Django settings.

    Returns:
        Dict with ``MAX_ATTEMPTS`` and ``LOCKOUT_DURATION`` keys.
    """
    return getattr(settings, "AUTH_LOCKOUT", {})


def _max_attempts() -> int:
    """Return the configured maximum failed attempts before lockout.

    Returns:
        Integer threshold from settings, falling back to the default.
    """
    return int(_config().get("MAX_ATTEMPTS", _DEFAULT_MAX_ATTEMPTS))


def _lockout_duration() -> int:
    """Return the lockout duration in seconds.

    Returns:
        Duration in seconds. 0 means manual unlock only.
    """
    return int(_config().get("LOCKOUT_DURATION", _DEFAULT_LOCKOUT_DURATION))


def is_locked(email: str) -> bool:
    """Check whether the given email is currently locked out.

    Args:
        email: The email address to check.

    Returns:
        True if the account is locked, False otherwise.
    """
    return bool(cache.get(_LOCKED_KEY.format(email=email)))


def record_failed_attempt(email: str) -> None:
    """Record a failed login attempt and lock the account if threshold is reached.

    Uses ``cache.add`` to initialize the counter on the first attempt, then
    ``cache.incr`` for subsequent increments — both map to atomic Redis operations.
    If the counter reaches ``MAX_ATTEMPTS``, sets the lockout flag.
    When ``LOCKOUT_DURATION`` is 0, keys have no TTL (manual unlock required).
    When ``MAX_ATTEMPTS`` is 0, lockout is disabled and this function is a no-op.

    Args:
        email: The email address that failed authentication.
    """
    duration = _lockout_duration()
    attempts_key = _ATTEMPTS_KEY.format(email=email)
    timeout = duration if duration > 0 else None

    if _max_attempts() == 0:
        return

    # cache.add sets the key only if it does not exist (atomic)
    # cache.incr maps to Redis INCR (atomic)
    if not cache.add(attempts_key, 1, timeout=timeout):
        try:
            new_count = cache.incr(attempts_key)
        except ValueError:
            # Key expired between add and incr — treat as first attempt
            cache.set(attempts_key, 1, timeout=timeout)
            new_count = 1
    else:
        new_count = 1

    if new_count >= _max_attempts():
        locked_key = _LOCKED_KEY.format(email=email)
        cache.set(locked_key, 1, timeout=timeout)


def clear_lockout(email: str) -> None:
    """Clear all lockout state for the given email.

    Called on successful login or manual admin unlock.

    Args:
        email: The email address to unlock.
    """
    cache.delete(_ATTEMPTS_KEY.format(email=email))
    cache.delete(_LOCKED_KEY.format(email=email))
