"""Custom exception handler for consistent API error responses."""

import logging
from typing import Any

from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Wrap DRF's default handler to produce a standard error envelope."""
    response = drf_exception_handler(exc, context)

    if response is None:
        return None

    code = _extract_code(exc)
    _log_exception(exc, context, response)

    response.data = {
        "status": "ERROR",
        "code": code,
        "data": response.data,
    }

    return response


def _log_exception(exc: Exception, context: dict[str, Any], response: Response) -> None:
    """Log the exception with request context.

    Uses WARNING for 4xx status codes and ERROR for 5xx.
    """
    request: Request | None = context.get("request")
    user = str(getattr(request, "user", "anonymous")) if request else "unknown"
    method = getattr(request, "method", "unknown") if request else "unknown"
    path = getattr(request, "path", "unknown") if request else "unknown"

    extra = {
        "user": user,
        "method": method,
        "path": path,
        "status_code": response.status_code,
        "exception_type": type(exc).__name__,
    }

    message = f"{type(exc).__name__}: {exc}"

    if response.status_code >= 500:
        logger.error(message, extra=extra)
    else:
        logger.warning(message, extra=extra)


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

    if hasattr(exc.detail, "code"):
        return str(exc.detail.code)

    return str(getattr(exc, "code", exc.default_code))
