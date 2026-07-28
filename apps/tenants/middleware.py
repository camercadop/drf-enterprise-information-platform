"""Middleware that cleans up tenant scope bound during authentication."""

from typing import Any

from django.http import HttpRequest, HttpResponse
from opentelemetry import trace

from core.base.context import get_bound_scope, unbind_scope


class TenantContextMiddleware:
    """Unbinds the tenant scope ContextVar after the response is generated.

    TenantJWTAuthentication binds the scope and stores the reset token
    on the request. This middleware ensures cleanup happens regardless
    of whether the view succeeds or raises.

    Must be placed after AuthenticationMiddleware in the MIDDLEWARE list.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            response: HttpResponse = self.get_response(request)
        finally:
            token = getattr(request, "_scope_token", None)
            if token is not None:
                unbind_scope(token)

        return response


class TenantTelemetryMiddleware:
    """Injects tenant_id into the active OpenTelemetry span.

    Reads tenant_id from the bound scope (set by TenantJWTAuthentication)
    and sets it as a span attribute on the current span. Must be placed
    after TenantContextMiddleware in the MIDDLEWARE list.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        scope = get_bound_scope()
        tenant_id = scope.get("tenant_id")
        if tenant_id is not None:
            span = trace.get_current_span()
            span.set_attribute("tenant.id", str(tenant_id))
        return self.get_response(request)
