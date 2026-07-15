import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.tenants import (
    TenantFactory,
    TenantMembershipFactory,
    TenantRoleFactory,
)


class TestLoginView(BaseActionAPITest):
    url = "/api/auth/login/"

    @pytest.fixture(autouse=True)
    def _setup_base(self, api_client: APIClient, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = api_client
        self.user = user
        self.membership = membership

    def test_login_single_tenant(self) -> None:
        response = self.client.post(
            self.url, {"email": self.user.email, "password": "TestPass123!"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["email"] == self.user.email
        assert response.data["user"]["tenant_id"] == str(self.membership.tenant_id)

    def test_login_multi_tenant_with_tenant_id(self) -> None:
        second_tenant = TenantFactory()
        second_role = TenantRoleFactory(tenant=second_tenant)
        TenantMembershipFactory(user=self.user, tenant=second_tenant, role=second_role)

        response = self.client.post(
            self.url,
            {
                "email": self.user.email,
                "password": "TestPass123!",
                "tenant_id": str(self.membership.tenant_id),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["tenant_id"] == str(self.membership.tenant_id)

    def test_login_multi_tenant_without_tenant_id_fails(self) -> None:
        second_tenant = TenantFactory()
        second_role = TenantRoleFactory(tenant=second_tenant)
        TenantMembershipFactory(user=self.user, tenant=second_tenant, role=second_role)

        response = self.client.post(
            self.url, {"email": self.user.email, "password": "TestPass123!"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_invalid_credentials(self) -> None:
        response = self.client.post(
            self.url, {"email": self.user.email, "password": "WrongPassword1!"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_no_membership(self) -> None:
        TenantMembership.objects.filter(user=self.user).delete()

        response = self.client.post(
            self.url, {"email": self.user.email, "password": "TestPass123!"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_invalid_tenant_id(self) -> None:
        other_tenant = TenantFactory()

        response = self.client.post(
            self.url,
            {
                "email": self.user.email,
                "password": "TestPass123!",
                "tenant_id": str(other_tenant.pk),
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
