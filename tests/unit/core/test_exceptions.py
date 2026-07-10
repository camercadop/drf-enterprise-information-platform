from unittest.mock import MagicMock

from rest_framework import status
from rest_framework.exceptions import NotFound

from core.exceptions.api import (
    APIException,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    ThrottlingError,
    ValidationError,
)
from core.exceptions.handler import _extract_code, exception_handler


class TestCustomExceptions:
    def test_validation_error_defaults(self) -> None:
        exc = ValidationError()
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.code == "validation_error"

    def test_validation_error_custom_detail(self) -> None:
        exc = ValidationError(detail="Custom message")
        assert exc.detail == "Custom message"

    def test_not_found_error(self) -> None:
        exc = NotFoundError()
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.code == "not_found"

    def test_permission_denied_error(self) -> None:
        exc = PermissionDeniedError()
        assert exc.status_code == status.HTTP_403_FORBIDDEN

    def test_authentication_error(self) -> None:
        exc = AuthenticationError()
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

    def test_throttling_error(self) -> None:
        exc = ThrottlingError()
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_base_api_exception(self) -> None:
        exc = APIException()
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestExceptionHandler:
    def test_wraps_response_in_envelope(self) -> None:
        exc = NotFound("Not found")
        context = {"view": MagicMock(), "request": MagicMock()}
        response = exception_handler(exc, context)

        assert response is not None
        assert response.data["status"] == "ERROR"
        assert "code" in response.data
        assert "data" in response.data

    def test_returns_none_for_unhandled(self) -> None:
        exc = RuntimeError("unexpected")
        context = {"view": MagicMock(), "request": MagicMock()}
        response = exception_handler(exc, context)
        assert response is None


class TestExtractCode:
    def test_non_api_exception(self) -> None:
        assert _extract_code(RuntimeError("oops")) == "error"

    def test_string_detail(self) -> None:
        exc = NotFound("gone")
        assert _extract_code(exc) == "not_found"

    def test_list_detail(self) -> None:
        exc = NotFound(["first", "second"])
        code = _extract_code(exc)
        assert isinstance(code, str)
