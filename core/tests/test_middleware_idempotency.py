"""Tests for core.middleware.idempotency."""

import json
from unittest.mock import MagicMock, patch

from django.http import HttpResponse

from core.middleware.idempotency import (
    IdempotencyMiddleware,
    STATUS_COMPLETE,
    STATUS_IN_FLIGHT,
    _redis_key,
)


def _make_request(
    method: str = "POST",
    authenticated: bool = True,
    idempotency_key: str | None = None,
    user_id: int = 1,
) -> MagicMock:
    """Build a minimal mock HttpRequest."""
    request = MagicMock()
    request.method = method
    request.path = "/api/resource/"
    request.user.pk = user_id
    request.user.is_authenticated = authenticated
    request.META = {}
    if idempotency_key:
        request.META["HTTP_X_IDEMPOTENCY_KEY"] = idempotency_key
    return request


def _make_middleware(status_code: int = 201, body: str = '{"id": "abc"}') -> IdempotencyMiddleware:
    """Build middleware with a simple get_response stub."""
    response = HttpResponse(content=body, status=status_code, content_type="application/json")
    return IdempotencyMiddleware(get_response=lambda r: response)


class TestRedisKey:
    def test_format(self) -> None:
        assert _redis_key(42, "my-key") == "idempotency:42:my-key"

    def test_different_users_produce_different_keys(self) -> None:
        assert _redis_key(1, "key") != _redis_key(2, "key")

    def test_different_keys_produce_different_results(self) -> None:
        assert _redis_key(1, "key-a") != _redis_key(1, "key-b")


class TestIdempotencyMiddlewarePassThrough:
    def test_skips_unguarded_method(self) -> None:
        middleware = _make_middleware()
        request = _make_request(method="GET")
        with patch("core.middleware.idempotency.get_redis_client") as mock_redis:
            response = middleware(request)
        mock_redis.assert_not_called()
        assert response.status_code == 201

    def test_skips_unauthenticated_request(self) -> None:
        middleware = _make_middleware()
        request = _make_request(authenticated=False, idempotency_key="key-1")
        with patch("core.middleware.idempotency.get_redis_client") as mock_redis:
            response = middleware(request)
        mock_redis.assert_not_called()
        assert response.status_code == 201

    def test_skips_when_header_absent_and_not_required(self) -> None:
        middleware = _make_middleware()
        request = _make_request()
        with patch("core.middleware.idempotency.get_redis_client") as mock_redis:
            with patch("core.middleware.idempotency._config", return_value={"REQUIRE_HEADER": False}):
                response = middleware(request)
        mock_redis.assert_not_called()
        assert response.status_code == 201


class TestIdempotencyMiddlewareRequireHeader:
    def test_returns_400_when_header_required_and_absent(self) -> None:
        middleware = _make_middleware()
        request = _make_request()
        with patch("core.middleware.idempotency._config", return_value={"REQUIRE_HEADER": True}):
            response = middleware(request)
        assert response.status_code == 400
        assert "X-Idempotency-Key" in json.loads(response.content)["detail"]


class TestIdempotencyMiddlewareInFlight:
    def test_returns_409_when_key_is_in_flight(self) -> None:
        middleware = _make_middleware()
        request = _make_request(idempotency_key="key-1")
        cached = json.dumps({"status": STATUS_IN_FLIGHT})
        mock_client = MagicMock()
        mock_client.get.return_value = cached
        with patch("core.middleware.idempotency.get_redis_client", return_value=mock_client):
            response = middleware(request)
        assert response.status_code == 409
        assert "already being processed" in json.loads(response.content)["detail"]


class TestIdempotencyMiddlewareCacheHit:
    def test_returns_cached_response_with_original_status_code(self) -> None:
        middleware = _make_middleware()
        request = _make_request(idempotency_key="key-1")
        cached = json.dumps({
            "status": STATUS_COMPLETE,
            "status_code": 201,
            "body": '{"id": "abc"}',
            "content_type": "application/json",
        })
        mock_client = MagicMock()
        mock_client.get.return_value = cached
        with patch("core.middleware.idempotency.get_redis_client", return_value=mock_client):
            response = middleware(request)
        assert response.status_code == 201
        assert json.loads(response.content) == {"id": "abc"}

    def test_preserves_non_201_status_code(self) -> None:
        middleware = _make_middleware()
        request = _make_request(idempotency_key="key-1")
        cached = json.dumps({
            "status": STATUS_COMPLETE,
            "status_code": 200,
            "body": '{"updated": true}',
            "content_type": "application/json",
        })
        mock_client = MagicMock()
        mock_client.get.return_value = cached
        with patch("core.middleware.idempotency.get_redis_client", return_value=mock_client):
            response = middleware(request)
        assert response.status_code == 200


class TestIdempotencyMiddlewareFirstRequest:
    def test_marks_in_flight_then_stores_complete(self) -> None:
        middleware = _make_middleware(status_code=201, body='{"id": "abc"}')
        request = _make_request(idempotency_key="key-1")
        mock_client = MagicMock()
        mock_client.get.return_value = None
        with patch("core.middleware.idempotency.get_redis_client", return_value=mock_client):
            response = middleware(request)

        assert response.status_code == 201
        assert mock_client.set.call_count == 2

        first_call_payload = json.loads(mock_client.set.call_args_list[0][0][1])
        assert first_call_payload["status"] == STATUS_IN_FLIGHT

        second_call_payload = json.loads(mock_client.set.call_args_list[1][0][1])
        assert second_call_payload["status"] == STATUS_COMPLETE
        assert second_call_payload["status_code"] == 201
        assert second_call_payload["body"] == '{"id": "abc"}'

    def test_uses_configured_ttl(self) -> None:
        middleware = _make_middleware()
        request = _make_request(idempotency_key="key-1")
        mock_client = MagicMock()
        mock_client.get.return_value = None
        with patch("core.middleware.idempotency.get_redis_client", return_value=mock_client):
            with patch("core.middleware.idempotency._config", return_value={"TTL": 3600}):
                middleware(request)

        for call in mock_client.set.call_args_list:
            assert call[1]["ex"] == 3600

    def test_redis_key_scoped_to_user(self) -> None:
        middleware = _make_middleware()
        request = _make_request(idempotency_key="key-1", user_id=99)
        mock_client = MagicMock()
        mock_client.get.return_value = None
        with patch("core.middleware.idempotency.get_redis_client", return_value=mock_client):
            middleware(request)

        used_key = mock_client.get.call_args[0][0]
        assert used_key == "idempotency:99:key-1"
