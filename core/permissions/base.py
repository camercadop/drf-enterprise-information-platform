"""
Base permission classes for the enterprise platform.
"""

import logging
from typing import Any

from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import BasePermission as DRFBasePermission
from rest_framework.request import Request

logger = logging.getLogger(__name__)


class BasePermission(DRFBasePermission):
    """
    Base permission class with common functionality.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request: Request, view: Any) -> bool:
        return True

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        """
        Check if the user has permission to access the object.
        Override in child classes.
        """
        return self.has_permission(request, view)

    def _log_denied(self, request: Request, view: Any, reason: str = "") -> None:
        """Log a permission denied event with request context."""
        logger.warning(
            "Permission denied: %s",
            reason or self.message,
            extra={
                "user": str(request.user),
                "method": request.method,
                "path": request.path,
                "permission_class": type(self).__name__,
                "view": type(view).__name__,
            },
        )

    def check_ownership(
        self, request: Request, obj: Any, owner_field: str = "created_by"
    ) -> bool:
        """
        Check if the request user owns the object.
        """
        if not hasattr(obj, owner_field):
            return False
        owner: bool = getattr(obj, owner_field) == request.user
        return owner


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission that allows read access to any request,
    but write access only to the owner of the object.
    """

    message = "You must be the owner of this object to edit it."

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in SAFE_METHODS:
            return True

        allowed = self.check_ownership(request, obj)
        if not allowed:
            self._log_denied(request, view)
        return allowed


class IsSuperUser(BasePermission):
    """Allow access only to superusers."""

    message = "Only platform administrators can perform this action."

    def has_permission(self, request: Request, view: Any) -> bool:
        allowed = bool(request.user and request.user.is_superuser)
        if not allowed:
            self._log_denied(request, view)
        return allowed
