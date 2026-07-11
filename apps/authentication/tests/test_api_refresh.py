import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import TenantMembership, User
from tests.base import BaseActionAPITest


class TestRefreshView(BaseActionAPITest):
    url = "/api/auth/refresh/"

    @pytest.fixture(autouse=True)
    def _setup_base(self, api_client: APIClient, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = api_client
        self.user = user
        self.membership = membership

    def test_refresh_valid_token(self) -> None:
        login_response = self.client.post(
            "/api/auth/login/", {"email": self.user.email, "password": "TestPass123!"}
        )
        refresh_token = login_response.data["refresh"]

        response = self.client.post(self.url, {"refresh": refresh_token})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_invalid_token(self) -> None:
        response = self.client.post(self.url, {"refresh": "invalid-token"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_blacklisted_token(self) -> None:
        login_response = self.client.post(
            "/api/auth/login/", {"email": self.user.email, "password": "TestPass123!"}
        )
        refresh_token = login_response.data["refresh"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        self.client.post("/api/auth/logout/", {"refresh": refresh_token})

        self.client.credentials()
        response = self.client.post(self.url, {"refresh": refresh_token})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
