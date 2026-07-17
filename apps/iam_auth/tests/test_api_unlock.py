import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.tenants import TenantMembershipFactory, TenantRoleFactory
from tests.factories.users import UserFactory


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Clear cache before each test to avoid state leakage."""
    cache.clear()


class TestUnlockAccountView(BaseActionAPITest):
    """Tests for POST /api/auth/unlock/{email}/."""

    url = "/api/auth/unlock/"

    @pytest.fixture(autouse=True)
    def _setup_base(self, auth_client: APIClient, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = auth_client
        self.user = user
        self.membership = membership

    def test_smoke(self) -> None:
        response = self.client.post(f"{self.url}someone@example.com/")
        assert response.status_code // 100 in (2, 4)

    def test_tenant_admin_can_unlock_other_user(self) -> None:
        self.membership.is_admin = True
        self.membership.save()

        target = UserFactory()
        cache.set(f"auth:lockout:locked:{target.email}", 1)

        response = self.client.post(f"{self.url}{target.email}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not cache.get(f"auth:lockout:locked:{target.email}")

    def test_tenant_admin_cannot_unlock_own_account(self) -> None:
        self.membership.is_admin = True
        self.membership.save()

        cache.set(f"auth:lockout:locked:{self.user.email}", 1)

        response = self.client.post(f"{self.url}{self.user.email}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert cache.get(f"auth:lockout:locked:{self.user.email}")

    def test_non_admin_member_cannot_unlock(self) -> None:
        self.membership.is_admin = False
        self.membership.save()

        target = UserFactory()
        cache.set(f"auth:lockout:locked:{target.email}", 1)

        response = self.client.post(f"{self.url}{target.email}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert cache.get(f"auth:lockout:locked:{target.email}")

    def test_unauthenticated_cannot_unlock(self, api_client: APIClient) -> None:
        target = UserFactory()
        cache.set(f"auth:lockout:locked:{target.email}", 1)

        response = api_client.post(f"{self.url}{target.email}/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_superuser_can_unlock_any_account(
        self, superuser_client: APIClient, superuser: User
    ) -> None:
        target = UserFactory()
        cache.set(f"auth:lockout:locked:{target.email}", 1)

        response = superuser_client.post(f"{self.url}{target.email}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not cache.get(f"auth:lockout:locked:{target.email}")

    def test_superuser_cannot_unlock_own_account(
        self, superuser_client: APIClient, superuser: User
    ) -> None:
        cache.set(f"auth:lockout:locked:{superuser.email}", 1)

        response = superuser_client.post(f"{self.url}{superuser.email}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unlock_non_locked_account_succeeds(self) -> None:
        self.membership.is_admin = True
        self.membership.save()

        target = UserFactory()

        response = self.client.post(f"{self.url}{target.email}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
