"""Tests for core.middleware.rate_limit."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpResponse

from core.exceptions.api import ThrottlingError
from core.middleware.rate_limit import FixedWindowRateLimitMiddleware


def _make_request(
    path: str = "/api/resource/",
    authenticated: bool = True,
    user_id: int = 1,
    method: str = "GET",
) -> MagicMock:
    """Build a minimal mock HttpRequest."""
    request = MagicMock()
    request.path = path
    request.method = method
    request.user.is_authenticated = authenticated
    request.user.pk = user_id
    request.META = {}
    return request


def _make_middleware(get_response: callable | None = None) -> FixedWindowRateLimitMiddleware:
    """Build middleware with a simple get_response stub."""
    response = HttpResponse(status=200)
    return FixedWindowRateLimitMiddleware(get_response=get_response or (lambda r: response))


class TestParseRate:
    def test_valid_rates(self, subtests: Any) -> None:
        """Test that valid rate strings are parsed correctly."""
        middleware = _make_middleware()
        cases = [
            ("10/minute", (10, 60)),
            ("5/second", (5, 1)),
            ("100/hour", (100, 3600)),
            ("1000/day", (1000, 86400)),
            ("0/minute", (0, 60)),
        ]
        for rate, expected in cases:
            with subtests.test(rate=rate):
                assert middleware._parse_rate(rate) == expected

    def test_invalid_format_raises(self) -> None:
        """Test that an invalid rate format raises ValueError."""
        with pytest.raises(ValueError):
            _make_middleware()._parse_rate("invalid")

    def test_invalid_period_raises(self) -> None:
        """Test that an unsupported period raises ValueError."""
        with pytest.raises(ValueError):
            _make_middleware()._parse_rate("10/week")


class TestGetIdent:
    def test_authenticated_user(self) -> None:
        """Test that authenticated requests are identified by user ID."""
        request = _make_request(authenticated=True, user_id=42)
        assert _make_middleware()._get_ident(request) == "user:42"

    def test_unauthenticated_user(self) -> None:
        """Test that unauthenticated requests are identified by IP address."""
        request = _make_request(authenticated=False)
        request.user = None
        with patch("core.middleware.rate_limit.get_client_ip", return_value="1.2.3.4"):
            assert _make_middleware()._get_ident(request) == "ip:1.2.3.4"


class TestGetScopeString:
    def test_disabled_returns_none(self) -> None:
        """Test that scope string is None when USE_BOUNDARY_SCOPE is False."""
        cfg = {"USE_BOUNDARY_SCOPE": False}
        assert _make_middleware()._get_scope_string(cfg) is None

    def test_enabled_no_scope_returns_none(self) -> None:
        """Test that scope string is None when no scope is bound."""
        cfg = {"USE_BOUNDARY_SCOPE": True}
        with patch("core.middleware.rate_limit.get_bound_scope", return_value=None):
            assert _make_middleware()._get_scope_string(cfg) is None

    def test_enabled_with_scope(self) -> None:
        """Test that scope string is built from bound scope dict."""
        cfg = {"USE_BOUNDARY_SCOPE": True}
        with patch(
            "core.middleware.rate_limit.get_bound_scope",
            return_value={"tenant_id": "abc-123"},
        ):
            result = _make_middleware()._get_scope_string(cfg)
        assert "tenant_id=abc-123" in result


class TestBuildKey:
    def test_without_scope(self) -> None:
        """Test key format without a scope prefix."""
        key = _make_middleware()._build_key(None, "user:1", "/api/resource/")
        assert key == "rate_limit:user:1:/api/resource/"

    def test_with_scope(self) -> None:
        """Test key format with a scope prefix."""
        key = _make_middleware()._build_key("tenant_id=abc", "user:1", "/api/resource/")
        assert key == "rate_limit:tenant_id=abc:user:1:/api/resource/"


class TestIsRateLimited:
    def test_all_cases(self, subtests: Any) -> None:
        """Test fixed-window rate limiting across first request, within limit, and exceeded."""
        cases = [
            ("first request not limited", True, None, False),
            ("exceeds limit", False, 11, True),
            ("within limit", False, 5, False),
        ]
        for desc, add_returns, incr_returns, expected in cases:
            with subtests.test(case=desc):
                with patch("core.middleware.rate_limit.cache") as mock_cache:
                    mock_cache.add.return_value = add_returns
                    if incr_returns is not None:
                        mock_cache.incr.return_value = incr_returns
                    else:
                        mock_cache.incr.side_effect = ValueError
                    assert _make_middleware().is_rate_limited("rate_limit:test", 10, 60) == expected


class TestIsViewOptedOut:
    def test_no_resolver_match(self) -> None:
        """Test that missing resolver_match returns False."""
        request = MagicMock()
        request.resolver_match = None
        assert _make_middleware()._is_view_opted_out(request) is False

    def test_no_view_class(self) -> None:
        """Test that missing view_class returns False."""
        request = MagicMock()
        request.resolver_match.func = MagicMock()
        request.resolver_match.func.view_class = None
        assert _make_middleware()._is_view_opted_out(request) is False

    def test_opted_out(self) -> None:
        """Test that rate_limit_enabled=False returns True."""
        request = MagicMock()
        view_class = MagicMock()
        view_class.rate_limit_enabled = False
        request.resolver_match.func.view_class = view_class
        assert _make_middleware()._is_view_opted_out(request) is True

    def test_not_opted_out(self) -> None:
        """Test that rate_limit_enabled=True returns False."""
        request = MagicMock()
        view_class = MagicMock()
        view_class.rate_limit_enabled = True
        request.resolver_match.func.view_class = view_class
        assert _make_middleware()._is_view_opted_out(request) is False


class TestIsSkippedPath:
    def test_all_cases(self, subtests: Any) -> None:
        """Test skip path matching across various configurations."""
        cases = [
            ("no skip paths", [], "/api/resource/", False),
            ("matching skip path", ["/api/health/"], "/api/health/", True),
            ("non-matching path", ["/api/health/"], "/api/resource/", False),
            ("prefix match", ["/api/webhooks/"], "/api/webhooks/stripe/", True),
        ]
        for desc, skip_paths, path, expected in cases:
            with subtests.test(case=desc):
                cfg = {"SKIP_PATHS": skip_paths}
                request = _make_request(path=path)
                assert _make_middleware()._is_skipped_path(request, cfg) is expected


class TestRateLimitMiddlewareDisabled:
    def test_passes_through_when_disabled(self) -> None:
        """Test that middleware is bypassed when ENABLED is False."""
        middleware = _make_middleware()
        request = _make_request()
        with patch("core.middleware.rate_limit.settings") as mock_settings:
            mock_settings.APP_RATE_LIMIT = {"ENABLED": False}
            response = middleware(request)
        assert response.status_code == 200


class TestRateLimitMiddlewarePassThrough:
    def test_allows_request_when_within_limit(self) -> None:
        """Test that requests within the rate limit pass through."""
        middleware = _make_middleware()
        request = _make_request()
        with patch("core.middleware.rate_limit.settings") as mock_settings:
            mock_settings.APP_RATE_LIMIT = {"ENABLED": True, "DEFAULT_RATE": "10/minute"}
            with patch("core.middleware.rate_limit.cache") as mock_cache:
                mock_cache.add.return_value = True
                response = middleware(request)
        assert response.status_code == 200


class TestRateLimitMiddlewareEnforcement:
    def test_raises_throttling_error_when_limited(self) -> None:
        """Test that exceeding the rate limit raises ThrottlingError."""
        middleware = _make_middleware()
        request = _make_request()
        with patch("core.middleware.rate_limit.settings") as mock_settings:
            mock_settings.APP_RATE_LIMIT = {"ENABLED": True, "DEFAULT_RATE": "10/minute"}
            with patch("core.middleware.rate_limit.cache") as mock_cache:
                mock_cache.add.return_value = False
                mock_cache.incr.return_value = 11
                mock_cache.ttl.return_value = 30
                with pytest.raises(ThrottlingError):
                    middleware(request)


class TestRateLimitMiddlewareViewOptOut:
    def test_skips_when_view_opted_out(self) -> None:
        """Test that middleware is bypassed when the view sets rate_limit_enabled=False."""
        middleware = _make_middleware()
        request = _make_request()
        view_class = MagicMock()
        view_class.rate_limit_enabled = False
        request.resolver_match.func.view_class = view_class
        with patch("core.middleware.rate_limit.settings") as mock_settings:
            mock_settings.APP_RATE_LIMIT = {"ENABLED": True}
            response = middleware(request)
        assert response.status_code == 200


class TestRateLimitMiddlewareSkippedPaths:
    def test_skips_matching_path(self) -> None:
        """Test that requests to skip-listed paths bypass rate limiting."""
        middleware = _make_middleware()
        request = _make_request(path="/api/health/")
        with patch("core.middleware.rate_limit.settings") as mock_settings:
            mock_settings.APP_RATE_LIMIT = {"ENABLED": True, "SKIP_PATHS": ["/api/health/"]}
            response = middleware(request)
        assert response.status_code == 200


class TestRateLimitMiddlewareBoundaryScope:
    def test_all_cases(self, subtests: Any) -> None:
        """Test that the Redis key is built with or without boundary scope."""
        cases = [
            ("scope enabled", True, {"tenant_id": "abc"}, "tenant_id=abc"),
            ("scope disabled", False, None, None),
        ]
        for desc, use_scope, bound_scope, expected_scope_fragment in cases:
            with subtests.test(case=desc):
                middleware = _make_middleware()
                request = _make_request()
                with patch("core.middleware.rate_limit.settings") as mock_settings:
                    mock_settings.APP_RATE_LIMIT = {
                        "ENABLED": True,
                        "DEFAULT_RATE": "10/minute",
                        "USE_BOUNDARY_SCOPE": use_scope,
                    }
                    with patch("core.middleware.rate_limit.get_bound_scope", return_value=bound_scope):
                        with patch("core.middleware.rate_limit.cache") as mock_cache:
                            mock_cache.add.return_value = True
                            middleware(request)
                            used_key: str = mock_cache.add.call_args[0][0]
                if expected_scope_fragment:
                    assert expected_scope_fragment in used_key
                else:
                    assert "tenant_id" not in used_key
