"""Rate limit middleware — enforces request rate limits via Redis."""

import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

from core.base.context import get_bound_scope
from core.exceptions.api import ThrottlingError
from core.utils.request import get_client_ip

logger = logging.getLogger(__name__)

_RATE_PERIODS: dict[str, int] = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}


def _config() -> dict[str, Any]:
    """Return the active rate limit configuration from Django settings.

    Returns:
        The ``APP_RATE_LIMIT`` settings dict, or an empty dict if not configured.
    """
    config: dict[str, Any] = getattr(settings, "APP_RATE_LIMIT", {})
    return config


def _parse_rate(rate: str) -> tuple[int, int]:
    """Parse a rate string into a count and window duration in seconds.

    Args:
        rate: A string in the format ``{count}/{period}``, e.g. ``"10/minute"``.
            Supported periods are ``second``, ``minute``, ``hour``, and ``day``.

    Returns:
        A tuple of ``(count, window_seconds)``.

    Raises:
        ValueError: If the rate string has an invalid format or period.
    """
    parts = rate.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid rate format: {rate}")
    count = int(parts[0])
    period = parts[1].lower()
    if period not in _RATE_PERIODS:
        raise ValueError(f"Invalid rate period: {period}")
    return count, _RATE_PERIODS[period]


def _get_ident(request: HttpRequest) -> str:
    """Return the identifier string for rate-limit key scoping.

    Authenticated requests are identified by user ID; unauthenticated
    requests are identified by client IP address.

    Args:
        request: The incoming HTTP request.

    Returns:
        A string in the form ``"user:{pk}"`` for authenticated requests,
        or ``"ip:{client_ip}"`` for unauthenticated requests.
    """
    if request.user and request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return f"ip:{get_client_ip(request)}"


def _get_scope_string(cfg: dict[str, Any]) -> str | None:
    """Return a scope identifier string for rate-limit key scoping.

    When ``USE_BOUNDARY_SCOPE`` is enabled and a boundary scope is bound,
    the scope dict is serialized into a deterministic string for use in
    rate-limit keys. Returns ``None`` when boundary scoping is disabled
    or no scope is bound.

    Args:
        cfg: The rate limit configuration dict.

    Returns:
        A sorted ``key=value`` string joined by ``|`` when boundary scope
        is active and non-empty, or ``None`` otherwise.
    """
    if not cfg.get("USE_BOUNDARY_SCOPE", False):
        return None
    scope = get_bound_scope()
    if not scope:
        return None
    items = sorted(scope.items())
    return "|".join(f"{k}={v}" for k, v in items)


def _build_key(scope: str | None, ident: str, path: str) -> str:
    """Build the Redis key for a rate-limit counter.

    Args:
        scope: The scope identifier string, or ``None`` if boundary scope
            is disabled or unbound.
        ident: The request identifier (e.g. ``"user:1"`` or ``"ip:1.2.3.4"``).
        path: The request path.

    Returns:
        A namespaced Redis key string. When scope is provided the format
        is ``rate_limit:{scope}:{ident}:{path}``; otherwise
        ``rate_limit:{ident}:{path}``.
    """
    if scope:
        return f"rate_limit:{scope}:{ident}:{path}"
    return f"rate_limit:{ident}:{path}"


def _is_rate_limited(key: str, count: int, window: int) -> bool:
    """Check whether the request exceeds the rate limit for the given key.

    Uses a fixed-window algorithm with atomic Redis operations. On the
    first request in a window the key is initialized; subsequent requests
    increment the counter. If the counter exceeds the limit the request
    is denied.

    Args:
        key: The Redis key for the rate-limit counter.
        count: The maximum number of requests allowed in the window.
        window: The window duration in seconds.

    Returns:
        ``True`` if the request is rate-limited, ``False`` otherwise.
    """
    added = cache.add(key, 1, timeout=window)
    if added:
        return False
    try:
        new_count: int = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        return False
    return new_count > count


def _is_view_opted_out(request: HttpRequest) -> bool:
    """Check whether the view has opted out of rate limiting.

    A view can disable rate limiting by setting ``rate_limit_enabled = False``
    on the view class.

    Args:
        request: The incoming HTTP request.

    Returns:
        ``True`` if the view class has ``rate_limit_enabled = False``,
        ``False`` otherwise (including when no view class is resolved).
    """
    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match is None:
        return False
    view_func = getattr(resolver_match, "func", None)
    if view_func is None:
        return False
    view_class = getattr(view_func, "view_class", None)
    if view_class is None:
        return False
    enabled: bool = getattr(view_class, "rate_limit_enabled", True)
    return enabled is False


def _is_skipped_path(request: HttpRequest, cfg: dict[str, Any]) -> bool:
    """Check whether the request path matches a configured skip prefix.

    Args:
        request: The incoming HTTP request.
        cfg: The rate limit configuration dict.

    Returns:
        ``True`` if the request path starts with any path in ``SKIP_PATHS``,
        ``False`` otherwise.
    """
    skip_paths: list[str] = cfg.get("SKIP_PATHS", [])
    path = request.path
    for skip_path in skip_paths:
        if path.startswith(skip_path):
            return True
    return False


class RateLimitMiddleware:
    """Enforces rate limits on incoming requests using a fixed-window algorithm backed by Redis.

    Requests are identified by user ID (for authenticated requests) or client IP
    (for unauthenticated requests). Rate limit keys are scoped by boundary scope
    when ``USE_BOUNDARY_SCOPE`` is enabled. Views can opt out by setting
    ``rate_limit_enabled = False`` on the view class.

    Configured via ``APP_RATE_LIMIT`` in Django settings.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Initialize the middleware with the next handler in the chain.

        Args:
            get_response: The next Django middleware or view callable.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process the request and enforce rate limits.

        Checks the rate limit configuration, view-level opt-out, and
        skipped paths before applying the fixed-window rate limit. Raises
        ``ThrottlingError`` when the limit is exceeded.

        Args:
            request: The incoming HTTP request.

        Returns:
            The HTTP response from the next handler or view.

        Raises:
            ThrottlingError: When the request exceeds the configured rate limit.
        """
        cfg = _config()

        if not cfg.get("ENABLED", False):
            return self.get_response(request)

        if _is_view_opted_out(request):
            return self.get_response(request)

        if _is_skipped_path(request, cfg):
            return self.get_response(request)

        rate_str: str = cfg.get("DEFAULT_RATE", "10/minute")
        count, window = _parse_rate(rate_str)

        ident = _get_ident(request)
        scope = _get_scope_string(cfg)
        key = _build_key(scope, ident, request.path)

        if _is_rate_limited(key, count, window):
            logger.warning(
                "Rate limit exceeded ident=%s path=%s",
                ident,
                request.path,
            )
            raise ThrottlingError()

        return self.get_response(request)
