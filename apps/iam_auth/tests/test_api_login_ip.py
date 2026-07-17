import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.iam_users.models import TenantMembership, User
from apps.tenants.models import TenantSetting
from tests.base import BaseActionAPITest


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Clear cache before each test to avoid state leakage."""
    cache.clear()


class TestLoginIPFilter(BaseActionAPITest):
    """Tests for IP allowlist/blocklist enforcement at login."""

    url = "/api/auth/login/"

    @pytest.fixture(autouse=True)
    def _setup_base(self, api_client: APIClient, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = api_client
        self.user = user
        self.membership = membership

    def _credentials(self) -> dict[str, str]:
        """Return valid login credentials for the test user."""
        return {"email": self.user.email, "password": "TestPass123!"}

    def _set_tenant_setting(self, key: str, value: str) -> None:
        """Create or update a TenantSetting for the test tenant."""
        TenantSetting.objects.update_or_create(
            tenant_id=self.membership.tenant_id,
            key=key,
            defaults={"value": value},
        )

    def test_blocked_ip_returns_403(self) -> None:
        self._set_tenant_setting("ip_blocklist", '["192.168.1.0/24"]')

        with patch("apps.iam_auth.serializers.get_client_ip", return_value="192.168.1.50"):
            response = self.client.post(self.url, self._credentials())

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "ip_blocked"

    def test_allowed_ip_in_allowlist_succeeds(self) -> None:
        self._set_tenant_setting("ip_allowlist", '["10.0.0.0/8"]')

        with patch("apps.iam_auth.serializers.get_client_ip", return_value="10.0.0.1"):
            response = self.client.post(self.url, self._credentials())

        assert response.status_code == status.HTTP_200_OK

    def test_ip_not_in_allowlist_returns_403(self) -> None:
        self._set_tenant_setting("ip_allowlist", '["10.0.0.0/8"]')

        with patch("apps.iam_auth.serializers.get_client_ip", return_value="8.8.8.8"):
            response = self.client.post(self.url, self._credentials())

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "ip_blocked"

    def test_blocklist_wins_over_allowlist(self) -> None:
        self._set_tenant_setting("ip_allowlist", '["10.0.0.0/8"]')
        self._set_tenant_setting("ip_blocklist", '["10.0.0.0/8"]')

        with patch("apps.iam_auth.serializers.get_client_ip", return_value="10.0.0.1"):
            response = self.client.post(self.url, self._credentials())

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "ip_blocked"

    def test_empty_allowlist_and_blocklist_allows_all(self) -> None:
        with patch("apps.iam_auth.serializers.get_client_ip", return_value="1.2.3.4"):
            response = self.client.post(self.url, self._credentials())

        assert response.status_code == status.HTTP_200_OK

    def test_ip_not_in_blocklist_is_allowed(self) -> None:
        self._set_tenant_setting("ip_blocklist", '["192.168.1.0/24"]')

        with patch("apps.iam_auth.serializers.get_client_ip", return_value="10.0.0.1"):
            response = self.client.post(self.url, self._credentials())

        assert response.status_code == status.HTTP_200_OK

    def test_unresolvable_ip_is_allowed(self) -> None:
        self._set_tenant_setting("ip_allowlist", '["10.0.0.0/8"]')

        with patch("apps.iam_auth.serializers.get_client_ip", return_value=""):
            response = self.client.post(self.url, self._credentials())

        assert response.status_code == status.HTTP_200_OK
