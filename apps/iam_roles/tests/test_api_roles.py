"""Tests for TenantRole CRUD endpoints."""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_roles.models import TenantRole
from apps.iam_users.models import TenantMembership
from tests.base import BaseCRUDAPITest
from tests.factories.tenants import TenantMembershipFactory, TenantRoleFactory


class TestTenantRoleViewSet(BaseCRUDAPITest):
    """Tests for /api/roles/ CRUD."""

    url = "/api/roles/"

    @pytest.fixture(autouse=True)
    def _setup_base(
        self,
        superuser_client: APIClient,
        superuser: Any,
        superuser_membership: TenantMembership,
    ) -> None:
        # Role write endpoints require is_admin=True; the fixture doesn't set it by default.
        superuser_membership.is_admin = True
        superuser_membership.save()

        self.client = superuser_client
        self.user = superuser
        self.membership = superuser_membership

    def create_instance(self) -> TenantRole:
        return TenantRoleFactory(tenant=self.membership.tenant, name="Custom Role")

    def valid_payloads(self) -> list[dict[str, Any]]:
        return [
            {"name": "Analyst", "description": "Read and report"},
            {"name": "Operator", "description": ""},
        ]

    def invalid_payloads(
        self,
    ) -> list[tuple[dict[str, Any], list[str | dict[str, str]] | None]]:
        return [
            ({"name": ""}, None),
        ]


@pytest.mark.django_db
class TestTenantRoleViewSetPermissions:
    """Tests for TenantRole write permission enforcement."""

    def test_non_admin_cannot_create_role(self, auth_client: APIClient) -> None:
        """Regular members cannot create roles."""
        response = auth_client.post(
            "/api/roles/", {"name": "New Role"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_authenticated_user_can_list_roles(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Authenticated users can list roles in their tenant."""
        TenantRoleFactory(tenant=membership.tenant, name="Viewer Role")
        response = auth_client.get("/api/roles/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTenantRoleSerializerEnforcement:
    """Tests for TenantRole serializer business rule enforcement."""

    @pytest.fixture(autouse=True)
    def _setup(
        self,
        superuser_client: APIClient,
        superuser_membership: TenantMembership,
    ) -> None:
        # Role write endpoints require is_admin=True; the fixture doesn't set it by default.
        superuser_membership.is_admin = True
        superuser_membership.save()
        self.client = superuser_client
        self.membership = superuser_membership

    def test_kind_is_immutable_after_creation(self) -> None:
        """Updating kind on an existing role returns 400."""
        role = TenantRoleFactory(
            tenant=self.membership.tenant, name="Immutable Role", kind="custom"
        )
        response = self.client.patch(
            f"/api/roles/{role.pk}/", {"kind": "admin"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["kind"][0].code == "invalid"

    def test_viewer_role_cannot_have_write_permissions(self) -> None:
        """Creating a viewer-kind role with a write permission returns 400."""
        response = self.client.post(
            "/api/roles/",
            {
                "name": "Bad Viewer",
                "kind": "viewer",
                "permissions": {"iam_roles.roles.create": 1},
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["permissions"][0].code == "invalid"

    def test_viewer_role_can_have_readonly_permissions(self) -> None:
        """Creating a viewer-kind role with only readonly permissions succeeds."""
        response = self.client.post(
            "/api/roles/",
            {
                "name": "Good Viewer",
                "kind": "viewer",
                "permissions": {"iam_roles.roles.view": 1},
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_updating_viewer_role_permissions_to_write_is_rejected(self) -> None:
        """Patching a viewer-kind role to add a write permission returns 400."""
        role = TenantRoleFactory(
            tenant=self.membership.tenant, name="Viewer Patch", kind="viewer"
        )
        response = self.client.patch(
            f"/api/roles/{role.pk}/",
            {"permissions": {"iam_roles.roles.delete": 1}},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["permissions"][0].code == "invalid"

    def test_duplicate_role_name_per_tenant_is_rejected(self) -> None:
        """Creating two roles with the same name in the same tenant returns 400."""
        TenantRoleFactory(tenant=self.membership.tenant, name="Duplicate")
        response = self.client.post(
            "/api/roles/", {"name": "Duplicate", "kind": "custom"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["GLOBAL_ERRORS"][0].code == "already_exists"
