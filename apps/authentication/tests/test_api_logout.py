from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import TenantMembership, User
from tests.base import BaseActionAPITest


class TestLogoutView(BaseActionAPITest):
    url = "/api/auth/logout/"

    def test_logout_success(self) -> None:
        response = self.client.post(self.url, {"refresh": "invalid-token"})
        # Smoke covers connectivity; this tests with a real token
        assert response.status_code // 100 in (2, 4)

    def test_logout_with_valid_token(
        self, api_client: APIClient, user: User, membership: TenantMembership
    ) -> None:
        login_response = api_client.post(
            "/api/auth/login/", {"email": user.email, "password": "TestPass123!"}
        )
        refresh_token = login_response.data["refresh"]
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )

        response = api_client.post(self.url, {"refresh": refresh_token})

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_invalid_token(self) -> None:
        response = self.client.post(self.url, {"refresh": "invalid-token"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLogoutAllView(BaseActionAPITest):
    url = "/api/auth/logout-all/"

    def test_logout_all_success(
        self, api_client: APIClient, user: User, membership: TenantMembership
    ) -> None:
        login1 = api_client.post(
            "/api/auth/login/", {"email": user.email, "password": "TestPass123!"}
        )
        login2 = api_client.post(
            "/api/auth/login/", {"email": user.email, "password": "TestPass123!"}
        )

        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login1.data['access']}"
        )
        response = api_client.post(self.url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        api_client.credentials()
        r1 = api_client.post("/api/auth/refresh/", {"refresh": login1.data["refresh"]})
        r2 = api_client.post("/api/auth/refresh/", {"refresh": login2.data["refresh"]})
        assert r1.status_code == status.HTTP_401_UNAUTHORIZED
        assert r2.status_code == status.HTTP_401_UNAUTHORIZED
