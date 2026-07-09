"""Custom renderer for consistent API response envelope."""

from typing import Any

from rest_framework.renderers import JSONRenderer


class APIRenderer(JSONRenderer):
    """Wraps all responses in a standard envelope: {status, data, ...}."""

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: dict[str, Any] | None = None,
    ) -> bytes:
        response = renderer_context.get("response") if renderer_context else None

        if response and response.status_code >= 400:
            # Error responses are already wrapped by the exception handler
            envelope = data
        else:
            envelope = {
                "status": "OK",
                "data": data,
            }

        result: bytes = super().render(envelope, accepted_media_type, renderer_context)
        return result
