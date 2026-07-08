"""
Base permission classes for the enterprise platform.
"""

from typing import Any

from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import BasePermission as DRFBasePermission
from rest_framework.request import Request


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

    def check_ownership(self, request: Request, obj: Any, owner_field: str = "created_by") -> bool:
        """
        Check if the request user owns the object.
        """
        if not hasattr(obj, owner_field):
            return False
        owner: bool = getattr(obj, owner_field) == request.user
        return owner

    def check_tenant_ownership(
        self, request: Request, obj: Any, tenant_field: str = "tenant"
    ) -> bool:
        """
        Check if the request user belongs to the object's tenant.
        """
        if not hasattr(obj, tenant_field):
            return False
        result: bool = request.user.tenants.filter(pk=getattr(obj, tenant_field).pk).exists()
        return result


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission that allows read access to any request,
    but write access only to the owner of the object.
    """

    message = "You must be the owner of this object to edit it."

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        # Read permissions are allowed to any request
        if request.method in SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return self.check_ownership(request, obj)


class IsTenantOwner(BasePermission):
    """
    Permission that allows access only to tenant owners.
    """

    message = "You must be a tenant owner to perform this action."

    def has_permission(self, request: Request, view: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            hasattr(request.user, "tenant_memberships")
            and request.user.tenant_memberships.filter(is_owner=True).exists()
        )

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        return self.has_permission(request, view)


class IsTeamMember(BasePermission):
    """
    Permission that allows access only to team members.
    """

    message = "You must be a team member to perform this action."

    def has_permission(self, request: Request, view: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            hasattr(request.user, "team_memberships")
            and request.user.team_memberships.exists()
        )

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        return self.has_permission(request, view)


class IsTenantAdmin(BasePermission):
    """
    Permission that allows access only to tenant admins.
    """

    message = "You must be a tenant admin to perform this action."

    def has_permission(self, request: Request, view: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            hasattr(request.user, "tenant_memberships")
            and request.user.tenant_memberships.filter(is_admin=True).exists()
        )

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        return self.has_permission(request, view)
