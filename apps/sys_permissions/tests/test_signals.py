"""Tests for default role seeding on tenant creation."""

import pytest

from apps.tenants.models import Tenant
from apps.users.models import TenantRole
from tests.factories.tenants import TenantFactory


@pytest.mark.django_db
class TestSeedDefaultRoles:
    def test_creates_four_default_roles(self) -> None:
        tenant = TenantFactory()
        roles = TenantRole.objects.filter(tenant=tenant)
        assert roles.count() == 4

    def test_creates_expected_role_names(self) -> None:
        tenant = TenantFactory()
        role_names = set(
            TenantRole.objects.filter(tenant=tenant).values_list("name", flat=True)
        )
        assert role_names == {"Owner", "Admin", "Member", "Viewer"}

    def test_owner_role_has_all_permissions(self) -> None:
        tenant = TenantFactory()
        owner_role = TenantRole.objects.get(tenant=tenant, name="Owner")
        assert len(owner_role.permissions) > 0
        for codename, value in owner_role.permissions.items():
            assert value == 1

    def test_viewer_role_has_only_readonly_permissions(self) -> None:
        from apps.sys_permissions.catalog import get_merged_catalog

        tenant = TenantFactory()
        viewer_role = TenantRole.objects.get(tenant=tenant, name="Viewer")
        merged = get_merged_catalog()
        for codename in viewer_role.permissions:
            assert merged[codename]["readonly"] is True

    def test_roles_have_permissions_as_dict(self) -> None:
        tenant = TenantFactory()
        for role in TenantRole.objects.filter(tenant=tenant):
            assert isinstance(role.permissions, dict)

    def test_no_roles_seeded_on_update(self) -> None:
        tenant = TenantFactory()
        initial_count = TenantRole.objects.filter(tenant=tenant).count()
        tenant.name = "Updated Name"
        tenant.save()
        assert TenantRole.objects.filter(tenant=tenant).count() == initial_count
