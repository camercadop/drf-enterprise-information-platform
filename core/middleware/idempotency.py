"""Idempotency middleware — deduplicates write requests via Redis."""

import json
import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from core.utils.redis import get_redis_client

logger = logging.getLogger(__name__)

HEADER = "HTTP_X_IDEMPOTENCY_KEY"
STATUS_IN_FLIGHT = "in_flight"
STATUS_COMPLETE = "complete"


def _config() -> dict[str, Any]:
    config: dict[str, Any] = getattr(settings, "APP_SAFETY_IDEMPOTENCY", {})
    return config


def _redis_key(user_id: Any, idempotency_key: str) -> str:
    """Build the Redis key for a given user and idempotency key.

    Args:
        user_id: The authenticated user's primary key.
        idempotency_key: The client-supplied idempotency key.

    Returns:
        A namespaced Redis key string.
    """
    return f"idempotency:{user_id}:{idempotency_key}"


class IdempotencyMiddleware:
    """Deduplicates write requests using a client-supplied idempotency key.

    Reads the ``X-Idempotency-Key`` header and uses it together with the
    authenticated user's ID to detect duplicate submissions. Responses are
    cached in Redis for a configurable TTL.

    Unauthenticated requests bypass idempotency entirely.
    Requests without the header are passed through unless ``REQUIRE_HEADER``
    is ``True``, in which case a ``400`` is returned.
    In-flight requests with the same key return ``409`` immediately.
    Completed requests return the original cached response.

    Configured via ``APP_SAFETY_IDEMPOTENCY`` in Django settings.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        cfg = _config()
        guarded_methods: list[str] = cfg.get("GUARDED_METHODS", ["POST", "PUT", "PATCH", "DELETE"])
        require_header: bool = cfg.get("REQUIRE_HEADER", False)
        ttl: int = cfg.get("TTL", 86400)

        if request.method not in guarded_methods:
            return self.get_response(request)

        if not request.user or not request.user.is_authenticated:
            return self.get_response(request)

        idempotency_key: str | None = request.META.get(HEADER)

        if not idempotency_key:
            if require_header:
                logger.warning(
                    "Missing X-Idempotency-Key user_id=%s path=%s",
                    request.user.pk,
                    request.path,
                )
                return HttpResponse(
                    content=json.dumps({"detail": "X-Idempotency-Key header is required."}),
                    status=400,
                    content_type="application/json",
                )
            return self.get_response(request)

        redis_key = _redis_key(request.user.pk, idempotency_key)
        client = get_redis_client()
        cached: bytes | str | None = client.get(redis_key)

        if cached:
            entry: dict[str, Any] = json.loads(cached)
            if entry["status"] == STATUS_IN_FLIGHT:
                logger.warning(
                    "Idempotency key in-flight user_id=%s key=%s",
                    request.user.pk,
                    idempotency_key,
                )
                return HttpResponse(
                    content=json.dumps({"detail": "A request with this idempotency key is already being processed."}),
                    status=409,
                    content_type="application/json",
                )
            logger.info(
                "Idempotency cache hit user_id=%s key=%s status_code=%s",
                request.user.pk,
                idempotency_key,
                entry["status_code"],
            )
            return HttpResponse(
                content=entry["body"],
                status=entry["status_code"],
                content_type=entry["content_type"],
            )

        client.set(redis_key, json.dumps({"status": STATUS_IN_FLIGHT}), ex=ttl)
        logger.info(
            "Idempotency key registered user_id=%s key=%s",
            request.user.pk,
            idempotency_key,
        )

        response = self.get_response(request)

        entry = {
            "status": STATUS_COMPLETE,
            "status_code": response.status_code,
            "body": response.content.decode("utf-8"),
            "content_type": response.get("Content-Type", "application/json"),
        }
        client.set(redis_key, json.dumps(entry), ex=ttl)
        logger.info(
            "Idempotency response cached user_id=%s key=%s status_code=%s",
            request.user.pk,
            idempotency_key,
            response.status_code,
        )

        return response
