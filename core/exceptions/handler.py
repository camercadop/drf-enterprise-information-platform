"""Custom exception handler for consistent API error responses."""

from typing import Any

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Wrap DRF's default handler to produce a standard error envelope."""
    response = drf_exception_handler(exc, context)

    if response is None:
        return None

    code = _extract_code(exc)

    response.data = {
        "status": "ERROR",
        "code": code,
        "data": response.data,
    }

    return response


def _extract_code(exc: Exception) -> str:
    """Extract the most specific error code from the exception."""
    if not isinstance(exc, APIException):
        return "error"

    if isinstance(exc.detail, list):
        return str(exc.detail[0].code) if exc.detail else "error"

    if isinstance(exc.detail, dict):
        codes = exc.get_codes()
        if isinstance(codes, str):
            return codes
        if isinstance(codes, dict):
            for v in codes.values():
                if isinstance(v, str):
                    return v
                if isinstance(v, list) and v:
                    return str(v[0])
        return str(exc.default_code)

    return str(exc.detail.code)  # type: ignore[union-attr]
