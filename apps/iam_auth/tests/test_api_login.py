import pytest
from django.core.cache import cache
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_auth.throttling import LoginEmailThrottle, LoginIPThrottle
from apps.iam_auth.views import LoginView
from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.tenants import (
    TenantFactory,
    TenantMembershipFactory,
    TenantRoleFactory,
)


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Clear cache before each test to avoid state leakage."""
    cache.clear()


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

    def test_failed_login_sends_login_failed_signal(self) -> None:
        from apps.iam_auth.signals import login_failed
        with patch.object(login_failed, "send") as mock_send:
            self.client.post(
                self.url, {"email": self.user.email, "password": "WrongPassword1!"}
            )
            mock_send.assert_called_once_with(
                sender=LoginView, email=self.user.email
            )

    def test_locked_account_is_rejected(self) -> None:
        cache.set(f"auth:lockout:locked:{self.user.email}", 1)

        response = self.client.post(
            self.url, {"email": self.user.email, "password": "TestPass123!"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "account_locked"

    def test_successful_login_clears_lockout(self) -> None:
        cache.set(f"auth:lockout:attempts:{self.user.email}", 3)

        self.client.post(
            self.url, {"email": self.user.email, "password": "TestPass123!"}
        )

        assert cache.get(f"auth:lockout:attempts:{self.user.email}") is None

    def test_ip_throttle_returns_429(self) -> None:
        with patch.object(LoginIPThrottle, "allow_request", return_value=False), \
             patch.object(LoginIPThrottle, "wait", return_value=60.0):
            response = self.client.post(
                self.url, {"email": self.user.email, "password": "TestPass123!"}
            )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.data["code"] == "rate_limit_exceeded"

    def test_email_throttle_returns_429(self) -> None:
        with patch.object(LoginEmailThrottle, "allow_request", return_value=False), \
             patch.object(LoginEmailThrottle, "wait", return_value=60.0):
            response = self.client.post(
                self.url, {"email": self.user.email, "password": "TestPass123!"}
            )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.data["code"] == "rate_limit_exceeded"
