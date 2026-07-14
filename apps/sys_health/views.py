"""Health check views for liveness and readiness probes."""

from django.core.cache import cache
from django.db import connection
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def liveness(request: Request) -> Response:
    """Confirm the process is running.

    Returns 200 unconditionally. Used by orchestrator liveness probes
    to detect unresponsive processes.
    """
    return Response({"status": "alive"})


@api_view(["GET"])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def readiness(request: Request) -> Response:
    """Verify critical dependencies are reachable.

    Checks PostgreSQL and Redis connectivity. Returns 200 if all
    dependencies respond, 503 otherwise. Used by orchestrator readiness
    probes to remove instances from load balancer rotation.
    """
    errors: dict[str, str] = {}

    try:
        connection.ensure_connection()
    except Exception as exc:
        errors["database"] = str(exc)

    try:
        cache.set("_health_check", "1", timeout=5)
        if cache.get("_health_check") != "1":
            errors["cache"] = "read-back mismatch"
    except Exception as exc:
        errors["cache"] = str(exc)

    if errors:
        return Response({"status": "unavailable", "errors": errors}, status=503)

    return Response({"status": "ready"})
