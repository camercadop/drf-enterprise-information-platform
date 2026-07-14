"""JWT authentication with tenant scope binding.

Extends SimpleJWT's authentication to bind the tenant_id from the token
into the boundary scope ContextVar. This provides the second enforcement
layer (ORM-level via TenantManager) required by ADR-004.
"""

from typing import Any

from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token

from core.base.context import bind_scope


class TenantJWTAuthentication(JWTAuthentication):  # type: ignore[type-arg]
    """JWT authentication that binds tenant scope for ORM-level isolation.

    After successful token validation, extracts tenant_id from claims
    and binds it to the request-scoped ContextVar. TenantManager reads
    this value to enforce data isolation independently of the view layer.

    The scope token is stored on the request for cleanup by
    TenantContextMiddleware on the response phase.
    """

    def authenticate(self, request: Request) -> tuple[Any, Token] | None:
        """Authenticate and bind tenant scope from JWT claims."""
        result = super().authenticate(request)
        if result is None:
            return None

        _user, token = result
        tenant_id = token.get("tenant_id")
        if tenant_id:
            # Store on the Django HttpRequest (request._request) so that
            # TenantContextMiddleware can access it for cleanup.
            django_request = getattr(request, "_request", request)
            django_request._scope_token = bind_scope({"tenant_id": str(tenant_id)})  # type: ignore[attr-defined]

        return result  # type: ignore[no-any-return]
