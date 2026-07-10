from unittest.mock import MagicMock

from core.permissions.base import (
    BasePermission,
    IsOwnerOrReadOnly,
    IsSuperUser,
    IsTeamMember,
    IsTenantAdmin,
    IsTenantOwner,
)


class TestBasePermission:
    def setup_method(self) -> None:
        self.permission = BasePermission()

    def test_has_permission_default_true(self) -> None:
        request = MagicMock()
        view = MagicMock()
        assert self.permission.has_permission(request, view) is True

    def test_has_object_permission_delegates_to_has_permission(self) -> None:
        request = MagicMock()
        view = MagicMock()
        obj = MagicMock()
        assert self.permission.has_object_permission(request, view, obj) is True

    def test_check_ownership_true(self) -> None:
        request = MagicMock()
        obj = MagicMock()
        obj.created_by = request.user
        assert self.permission.check_ownership(request, obj) is True

    def test_check_ownership_false(self) -> None:
        request = MagicMock()
        obj = MagicMock()
        obj.created_by = MagicMock()
        assert self.permission.check_ownership(request, obj) is False

    def test_check_ownership_missing_field(self) -> None:
        request = MagicMock()
        obj = object()
        assert self.permission.check_ownership(request, obj) is False

    def test_check_ownership_custom_field(self) -> None:
        request = MagicMock()
        obj = MagicMock()
        obj.owner = request.user
        assert self.permission.check_ownership(request, obj, owner_field="owner") is True


class TestIsOwnerOrReadOnly:
    def setup_method(self) -> None:
        self.permission = IsOwnerOrReadOnly()

    def test_safe_method_allowed(self) -> None:
        request = MagicMock()
        request.method = "GET"
        obj = MagicMock()
        assert self.permission.has_object_permission(request, MagicMock(), obj) is True

    def test_unsafe_method_owner_allowed(self) -> None:
        request = MagicMock()
        request.method = "PUT"
        obj = MagicMock()
        obj.created_by = request.user
        assert self.permission.has_object_permission(request, MagicMock(), obj) is True

    def test_unsafe_method_non_owner_denied(self) -> None:
        request = MagicMock()
        request.method = "DELETE"
        obj = MagicMock()
        obj.created_by = MagicMock()
        assert self.permission.has_object_permission(request, MagicMock(), obj) is False


class TestIsSuperUser:
    def setup_method(self) -> None:
        self.permission = IsSuperUser()

    def test_superuser_allowed(self) -> None:
        request = MagicMock()
        request.user.is_superuser = True
        assert self.permission.has_permission(request, MagicMock()) is True

    def test_non_superuser_denied(self) -> None:
        request = MagicMock()
        request.user.is_superuser = False
        assert self.permission.has_permission(request, MagicMock()) is False

    def test_no_user_denied(self) -> None:
        request = MagicMock()
        request.user = None
        assert self.permission.has_permission(request, MagicMock()) is False


class TestIsTenantOwner:
    def setup_method(self) -> None:
        self.permission = IsTenantOwner()

    def test_unauthenticated_denied(self) -> None:
        request = MagicMock()
        request.user.is_authenticated = False
        assert self.permission.has_permission(request, MagicMock()) is False

    def test_no_user_denied(self) -> None:
        request = MagicMock()
        request.user = None
        assert self.permission.has_permission(request, MagicMock()) is False

    def test_owner_allowed(self) -> None:
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.tenant_memberships.filter.return_value.exists.return_value = True
        assert self.permission.has_permission(request, MagicMock()) is True

    def test_non_owner_denied(self) -> None:
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.tenant_memberships.filter.return_value.exists.return_value = False
        assert self.permission.has_permission(request, MagicMock()) is False


class TestIsTenantAdmin:
    def setup_method(self) -> None:
        self.permission = IsTenantAdmin()

    def test_admin_allowed(self) -> None:
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.tenant_memberships.filter.return_value.exists.return_value = True
        assert self.permission.has_permission(request, MagicMock()) is True

    def test_non_admin_denied(self) -> None:
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.tenant_memberships.filter.return_value.exists.return_value = False
        assert self.permission.has_permission(request, MagicMock()) is False


class TestIsTeamMember:
    def setup_method(self) -> None:
        self.permission = IsTeamMember()

    def test_member_allowed(self) -> None:
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.team_memberships.exists.return_value = True
        assert self.permission.has_permission(request, MagicMock()) is True

    def test_non_member_denied(self) -> None:
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.team_memberships.exists.return_value = False
        assert self.permission.has_permission(request, MagicMock()) is False
