"""Custom OpenAPI schema generation for the platform's response envelope."""

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema
from drf_spectacular.utils import Direction


class TenantJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """Registers TenantJWTAuthentication as a Bearer token scheme."""

    target_class = "apps.tenants.authentication.TenantJWTAuthentication"
    name = "TenantJWTAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }


class AutoSchema(SpectacularAutoSchema):
    """OpenAPI schema class that reflects the platform's response envelope.

    Use this as DEFAULT_SCHEMA_CLASS. Pagination shape is defined by
    each pagination class via get_paginated_response_schema.
    """

    def _get_response_bodies(
        self, direction: Direction = "response"
    ) -> dict[str, Any]:
        responses: dict[str, Any] = super()._get_response_bodies(direction)

        for status_code, response in responses.items():
            if not response or int(status_code) >= 400:
                continue

            content = response.get("content", {})
            for _media_type, media_obj in content.items():
                schema = media_obj.get("schema")
                if schema:
                    media_obj["schema"] = {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["OK"]},
                            "data": schema,
                        },
                        "required": ["status", "data"],
                    }

        return responses
