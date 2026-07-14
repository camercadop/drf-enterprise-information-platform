"""Middleware that binds tenant scope from JWT for ORM-level enforcement."""

from contextvars import Token
from typing import Any

from django.http import HttpRequest, HttpResponse

from core.base.context import bind_scope, unbind_scope


class TenantContextMiddleware:
    """Extracts tenant_id from the JWT and binds it as the active boundary scope.

    This middleware sets the ContextVar that TenantManager reads,
    providing the second enforcement layer required by ADR-004.

    Must be placed after AuthenticationMiddleware in the MIDDLEWARE list.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        token: Token[dict[str, Any] | None] | None = None
        tenant_id = self._extract_tenant_id(request)

        if tenant_id:
            token = bind_scope({"tenant_id": tenant_id})

        try:
            response: HttpResponse = self.get_response(request)
        finally:
            if token is not None:
                unbind_scope(token)

        return response

    def _extract_tenant_id(self, request: HttpRequest) -> str | None:
        """Extract tenant_id from the JWT claims on the request.

        DRF's JWTAuthentication sets request.auth to the validated token
        after authentication. This middleware runs before DRF view processing,
        so we access the auth attribute if DRF has already authenticated
        (via Django's AuthenticationMiddleware or DRF's perform_authentication).
        """
        auth = getattr(request, "auth", None)
        if auth and hasattr(auth, "get"):
            result: str | None = auth.get("tenant_id")
            return result
        return None
