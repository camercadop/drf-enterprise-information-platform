"""Rate limit middleware — enforces request rate limits via Redis."""

import logging
from abc import ABC, abstractmethod
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


class BaseRateLimitMiddleware(ABC):
    """Abstract base for rate limit middleware.

    Handles common plumbing: enabled check, view opt-out, skip paths, key
    building, and throttle raising. Subclasses implement ``is_rate_limited``
    with a specific algorithm.

    Configured via ``APP_RATE_LIMIT`` in Django settings.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    @abstractmethod
    def is_rate_limited(self, key: str, count: int, window: int) -> bool:
        """Return ``True`` if the request should be denied."""

    def _config(self) -> dict[str, Any]:
        """Return the active rate limit configuration from Django settings."""
        config: dict[str, Any] = getattr(settings, "APP_RATE_LIMIT", {})
        return config

    def _parse_rate(self, rate: str) -> tuple[int, int]:
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

    def _get_ident(self, request: HttpRequest) -> str:
        """Return the identifier string for rate-limit key scoping.

        Authenticated requests are identified by user ID; unauthenticated
        requests are identified by client IP address.

        Returns:
            A string in the form ``"user:{pk}"`` for authenticated requests,
            or ``"ip:{client_ip}"`` for unauthenticated requests.
        """
        if request.user and request.user.is_authenticated:
            return f"user:{request.user.pk}"
        return f"ip:{get_client_ip(request)}"

    def _get_scope_string(self, cfg: dict[str, Any]) -> str | None:
        """Return a scope identifier string for rate-limit key scoping.

        When ``USE_BOUNDARY_SCOPE`` is enabled and a boundary scope is bound,
        the scope dict is serialized into a deterministic string for use in
        rate-limit keys. Returns ``None`` when boundary scoping is disabled
        or no scope is bound.
        """
        if not cfg.get("USE_BOUNDARY_SCOPE", False):
            return None
        scope = get_bound_scope()
        if not scope:
            return None
        return "|".join(f"{k}={v}" for k, v in sorted(scope.items()))

    def _build_key(self, scope: str | None, ident: str, path: str) -> str:
        """Build the Redis key for a rate-limit counter.

        Returns:
            A namespaced Redis key string. When scope is provided the format
            is ``rate_limit:{scope}:{ident}:{path}``; otherwise
            ``rate_limit:{ident}:{path}``.
        """
        if scope:
            return f"rate_limit:{scope}:{ident}:{path}"
        return f"rate_limit:{ident}:{path}"

    def _is_view_opted_out(self, request: HttpRequest) -> bool:
        """Return ``True`` if the view class has ``rate_limit_enabled = False``."""
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

    def _is_skipped_path(self, request: HttpRequest, cfg: dict[str, Any]) -> bool:
        """Return ``True`` if the request path matches a configured skip prefix."""
        skip_paths: list[str] = cfg.get("SKIP_PATHS", [])
        return any(request.path.startswith(p) for p in skip_paths)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        cfg = self._config()

        if not cfg.get("ENABLED", False):
            return self.get_response(request)

        if self._is_view_opted_out(request):
            return self.get_response(request)

        if self._is_skipped_path(request, cfg):
            return self.get_response(request)

        rate_str: str = cfg.get("DEFAULT_RATE", "10/minute")
        count, window = self._parse_rate(rate_str)

        ident = self._get_ident(request)
        scope = self._get_scope_string(cfg)
        key = self._build_key(scope, ident, request.path)

        if self.is_rate_limited(key, count, window):
            logger.warning("Rate limit exceeded ident=%s path=%s", ident, request.path)
            retry_after = cache.ttl(key)
            raise ThrottlingError(
                retry_after=retry_after if retry_after and retry_after > 0 else window
            )

        return self.get_response(request)


class FixedWindowRateLimitMiddleware(BaseRateLimitMiddleware):
    """Enforces rate limits using a fixed-window algorithm backed by Redis."""

    def is_rate_limited(self, key: str, count: int, window: int) -> bool:
        """Check whether the request exceeds the rate limit for the given key.

        Uses a fixed-window algorithm with atomic Redis operations. On the
        first request in a window the key is initialized; subsequent requests
        increment the counter. If the counter exceeds the limit the request
        is denied.
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
