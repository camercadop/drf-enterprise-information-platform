"""Tests for the HasTenantPermission factory."""

from unittest.mock import MagicMock, patch

from apps.sys_permissions.permissions import HasTenantPermission


class TestHasTenantPermission:
    def setup_method(self) -> None:
        self.permission_class = HasTenantPermission("tenants.teams.create")
        self.permission = self.permission_class()
        self.view = MagicMock()

    def _make_request(
        self,
        authenticated: bool = True,
        tenant_id: str | None = "tenant-123",
    ) -> MagicMock:
        request = MagicMock()
        request.user.is_authenticated = authenticated
        if not authenticated:
            request.user = None
        return request

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_unauthenticated_denied(self, mock_get_tenant: MagicMock) -> None:
        request = MagicMock()
        request.user = None
        assert self.permission.has_permission(request, self.view) is False

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_no_tenant_context_denied(self, mock_get_tenant: MagicMock) -> None:
        mock_get_tenant.return_value = None
        request = MagicMock()
        request.user.is_authenticated = True
        assert self.permission.has_permission(request, self.view) is False

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_no_membership_denied(self, mock_get_tenant: MagicMock) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = None
        assert self.permission.has_permission(request, self.view) is False

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_admin_bypasses_permission_check(self, mock_get_tenant: MagicMock) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        membership = MagicMock()
        membership.is_admin = True
        membership.role.permissions = {}
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = membership
        assert self.permission.has_permission(request, self.view) is True

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_codename_with_value_1_allowed(self, mock_get_tenant: MagicMock) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        membership = MagicMock()
        membership.is_admin = False
        membership.role.permissions = {"tenants.access": 1, "tenants.teams.create": 1}
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = membership
        assert self.permission.has_permission(request, self.view) is True

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_codename_with_value_0_denied(self, mock_get_tenant: MagicMock) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        membership = MagicMock()
        membership.is_admin = False
        membership.role.permissions = {"tenants.access": 1, "tenants.teams.create": 0}
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = membership
        assert self.permission.has_permission(request, self.view) is False

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_codename_missing_denied(self, mock_get_tenant: MagicMock) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        membership = MagicMock()
        membership.is_admin = False
        membership.role.permissions = {"tenants.access": 1, "tenants.tenants.view": 1}
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = membership
        assert self.permission.has_permission(request, self.view) is False

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_empty_permissions_denied(self, mock_get_tenant: MagicMock) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        membership = MagicMock()
        membership.is_admin = False
        membership.role.permissions = {}
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = membership
        assert self.permission.has_permission(request, self.view) is False

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_none_permissions_denied(self, mock_get_tenant: MagicMock) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        membership = MagicMock()
        membership.is_admin = False
        membership.role.permissions = None
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = membership
        assert self.permission.has_permission(request, self.view) is False

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_access_denied_blocks_even_with_codename_granted(
        self, mock_get_tenant: MagicMock
    ) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        membership = MagicMock()
        membership.is_admin = False
        membership.role.permissions = {"tenants.access": 0, "tenants.teams.create": 1}
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = membership
        assert self.permission.has_permission(request, self.view) is False

    @patch("apps.sys_permissions.permissions.get_tenant_id")
    def test_access_missing_blocks_even_with_codename_granted(
        self, mock_get_tenant: MagicMock
    ) -> None:
        mock_get_tenant.return_value = "tenant-123"
        request = MagicMock()
        request.user.is_authenticated = True
        membership = MagicMock()
        membership.is_admin = False
        membership.role.permissions = {"tenants.teams.create": 1}
        request.user.memberships.filter.return_value.select_related.return_value.first.return_value = membership
        assert self.permission.has_permission(request, self.view) is False

    def test_factory_returns_unique_class_per_codename(self) -> None:
        cls_a = HasTenantPermission("tenants.teams.create")
        cls_b = HasTenantPermission("tenants.teams.delete")
        assert cls_a is not cls_b
        assert cls_a.__name__ != cls_b.__name__

    def test_permission_message_includes_codename(self) -> None:
        perm = HasTenantPermission("iam_users.members.invite")()
        assert "iam_users.members.invite" in perm.message
