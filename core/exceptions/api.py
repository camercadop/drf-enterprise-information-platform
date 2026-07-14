"""
Custom API exceptions for the enterprise platform.
"""

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException as DRFAPIException


class APIException(DRFAPIException):
    """
    Base API exception for all custom exceptions.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "A server error occurred."
    default_code = "server_error"

    def __init__(self, detail: Any = None, code: str | None = None):
        if detail is None:
            detail = self.default_detail
        self.detail = detail
        self.code = code or self.default_code


class ValidationError(APIException):
    """
    Exception raised for validation errors.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid input provided."
    default_code = "validation_error"

    def __init__(self, detail: Any = None, code: str | None = None):
        super().__init__(detail, code)


class NotFoundError(APIException):
    """
    Exception raised when a resource is not found.
    """

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = "not_found"

    def __init__(self, detail: Any = None, code: str | None = None):
        super().__init__(detail, code)


class PermissionDeniedError(APIException):
    """
    Exception raised when a user doesn't have permission to access a resource.
    """

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"

    def __init__(self, detail: Any = None, code: str | None = None):
        super().__init__(detail, code)


class AuthenticationError(APIException):
    """
    Exception raised when authentication fails.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Invalid credentials."
    default_code = "authentication_error"

    def __init__(self, detail: Any = None, code: str | None = None):
        super().__init__(detail, code)


class ThrottlingError(APIException):
    """
    Exception raised when rate limiting is exceeded.
    """

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many requests. Please try again later."
    default_code = "throttling_error"

    def __init__(self, detail: Any = None, code: str | None = None):
        super().__init__(detail, code)


class ConflictError(APIException):
    """Exception raised when an operation conflicts with the current resource state.

    Used for state transition guards: the requested transition has already been
    applied or the resource is not in the expected state for the operation.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Operation conflicts with current resource state."
    default_code = "conflict"

    def __init__(self, detail: Any = None, code: str | None = None):
        super().__init__(detail, code)
