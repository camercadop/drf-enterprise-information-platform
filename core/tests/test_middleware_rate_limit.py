"""Tests for core.middleware.rate_limit."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpResponse

from core.middleware.rate_limit import (
    RateLimitMiddleware,
    _build_key,
    _config,
    _get_ident,
    _get_scope_string,
    _is_rate_limited,
    _is_skipped_path,
    _is_view_opted_out,
    _parse_rate,
)
from core.exceptions.api import ThrottlingError


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


def _make_middleware(get_response: callable | None = None) -> RateLimitMiddleware:
    """Build middleware with a simple get_response stub."""
    response = HttpResponse(status=200)
    return RateLimitMiddleware(get_response=get_response or (lambda r: response))


class TestParseRate:
    def test_valid_rates(self, subtests: Any) -> None:
        cases = [
            ("10/minute", (10, 60)),
            ("5/second", (5, 1)),
            ("100/hour", (100, 3600)),
            ("1000/day", (1000, 86400)),
            ("0/minute", (0, 60)),
        ]
        for rate, expected in cases:
            with subtests.test(rate=rate):
                assert _parse_rate(rate) == expected

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_rate("invalid")

    def test_invalid_period_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_rate("10/week")


class TestGetIdent:
    def test_authenticated_user(self) -> None:
        request = _make_request(authenticated=True, user_id=42)
        assert _get_ident(request) == "user:42"

    def test_unauthenticated_user(self) -> None:
        request = _make_request(authenticated=False)
        request.user = None
        with patch("core.middleware.rate_limit.get_client_ip", return_value="1.2.3.4"):
            assert _get_ident(request) == "ip:1.2.3.4"


class TestGetScopeString:
    def test_disabled_returns_none(self) -> None:
        cfg = {"USE_BOUNDARY_SCOPE": False}
        assert _get_scope_string(cfg) is None

    def test_enabled_no_scope_returns_none(self) -> None:
        cfg = {"USE_BOUNDARY_SCOPE": True}
        with patch("core.middleware.rate_limit.get_bound_scope", return_value=None):
            assert _get_scope_string(cfg) is None

    def test_enabled_with_scope(self) -> None:
        cfg = {"USE_BOUNDARY_SCOPE": True}
        with patch(
            "core.middleware.rate_limit.get_bound_scope",
            return_value={"tenant_id": "abc-123"},
        ):
            result = _get_scope_string(cfg)
        assert "tenant_id=abc-123" in result


class TestBuildKey:
    def test_without_scope(self) -> None:
        key = _build_key(None, "user:1", "/api/resource/")
        assert key == "rate_limit:user:1:/api/resource/"

    def test_with_scope(self) -> None:
        key = _build_key("tenant_id=abc", "user:1", "/api/resource/")
        assert key == "rate_limit:tenant_id=abc:user:1:/api/resource/"


class TestIsRateLimited:
    def test_all_cases(self, subtests: Any) -> None:
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
                    assert _is_rate_limited("rate_limit:test", 10, 60) == expected


class TestIsViewOptedOut:
    def test_no_resolver_match(self) -> None:
        request = MagicMock()
        request.resolver_match = None
        assert _is_view_opted_out(request) is False

    def test_no_view_class(self) -> None:
        request = MagicMock()
        request.resolver_match.func = MagicMock()
        request.resolver_match.func.view_class = None
        assert _is_view_opted_out(request) is False

    def test_opted_out(self) -> None:
        request = MagicMock()
        view_class = MagicMock()
        view_class.rate_limit_enabled = False
        request.resolver_match.func.view_class = view_class
        assert _is_view_opted_out(request) is True

    def test_not_opted_out(self) -> None:
        request = MagicMock()
        view_class = MagicMock()
        view_class.rate_limit_enabled = True
        request.resolver_match.func.view_class = view_class
        assert _is_view_opted_out(request) is False


class TestIsSkippedPath:
    def test_all_cases(self, subtests: Any) -> None:
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
                assert _is_skipped_path(request, cfg) == expected


class TestConfig:
    def test_returns_settings_dict(self) -> None:
        with patch("core.middleware.rate_limit.settings") as mock_settings:
            mock_settings.APP_RATE_LIMIT = {"ENABLED": True}
            assert _config() == {"ENABLED": True}

    def test_returns_empty_dict_when_missing(self) -> None:
        with patch("core.middleware.rate_limit.settings") as mock_settings:
            mock_settings.APP_RATE_LIMIT = {}
            assert _config() == {}


class TestRateLimitMiddlewareDisabled:
    def test_passes_through_when_disabled(self) -> None:
        middleware = _make_middleware()
        request = _make_request()
        with patch("core.middleware.rate_limit._config", return_value={"ENABLED": False}):
            response = middleware(request)
        assert response.status_code == 200


class TestRateLimitMiddlewarePassThrough:
    def test_allows_request_when_within_limit(self) -> None:
        middleware = _make_middleware()
        request = _make_request()
        with patch("core.middleware.rate_limit._config", return_value={"ENABLED": True, "DEFAULT_RATE": "10/minute"}):
            with patch("core.middleware.rate_limit._is_rate_limited", return_value=False):
                response = middleware(request)
        assert response.status_code == 200


class TestRateLimitMiddlewareEnforcement:
    def test_raises_throttling_error_when_limited(self) -> None:
        middleware = _make_middleware()
        request = _make_request()
        with patch("core.middleware.rate_limit._config", return_value={"ENABLED": True, "DEFAULT_RATE": "10/minute"}):
            with patch("core.middleware.rate_limit._is_rate_limited", return_value=True):
                with pytest.raises(ThrottlingError):
                    middleware(request)


class TestRateLimitMiddlewareViewOptOut:
    def test_skips_when_view_opted_out(self) -> None:
        middleware = _make_middleware()
        request = _make_request()
        view_class = MagicMock()
        view_class.rate_limit_enabled = False
        request.resolver_match.func.view_class = view_class
        with patch("core.middleware.rate_limit._config", return_value={"ENABLED": True}):
            response = middleware(request)
        assert response.status_code == 200


class TestRateLimitMiddlewareSkippedPaths:
    def test_skips_matching_path(self) -> None:
        middleware = _make_middleware()
        request = _make_request(path="/api/health/")
        with patch("core.middleware.rate_limit._config", return_value={"ENABLED": True, "SKIP_PATHS": ["/api/health/"]}):
            response = middleware(request)
        assert response.status_code == 200


class TestRateLimitMiddlewareBoundaryScope:
    def test_all_cases(self, subtests: Any) -> None:
        cases = [
            ("scope enabled", True, "tenant_id=abc", "tenant_id=abc", "user:1", "/api/resource/"),
            ("scope disabled", False, None, None, "user:1", "/api/resource/"),
        ]
        for desc, use_scope, scope_str, expected_scope, expected_ident, expected_path in cases:
            with subtests.test(case=desc):
                middleware = _make_middleware()
                request = _make_request()
                with patch("core.middleware.rate_limit._config", return_value={"ENABLED": True, "DEFAULT_RATE": "10/minute", "USE_BOUNDARY_SCOPE": use_scope}):
                    with patch("core.middleware.rate_limit._get_scope_string", return_value=scope_str):
                        with patch("core.middleware.rate_limit._is_rate_limited", return_value=False):
                            with patch("core.middleware.rate_limit._build_key") as mock_build_key:
                                mock_build_key.return_value = "rate_limit:test"
                                middleware(request)
                                mock_build_key.assert_called_once_with(
                                    expected_scope, expected_ident, expected_path
                                )