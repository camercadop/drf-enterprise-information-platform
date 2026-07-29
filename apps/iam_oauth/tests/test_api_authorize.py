import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.iam_oauth import OAuth2ClientFactory, PublicOAuth2ClientFactory


class TestAuthorizeView(BaseActionAPITest):
    url = "/api/oauth/authorize/"
    http_method = "get"

    @pytest.fixture(autouse=True)
    def _setup_base(self, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        token = AccessToken.for_user(user)
        token["tenant_id"] = str(membership.tenant_id)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.user = user
        self.membership = membership

    def test_issues_code_and_redirects(self) -> None:
        client = OAuth2ClientFactory(tenant=self.membership.tenant)
        response = self.client.get(
            self.url,
            {
                "response_type": "code",
                "client_id": client.client_id,
                "redirect_uri": "https://example.com/callback",
            },
        )
        assert response.status_code == status.HTTP_302_FOUND
        assert "code=" in response["Location"]

    def test_state_echoed_in_redirect(self) -> None:
        client = OAuth2ClientFactory(tenant=self.membership.tenant)
        response = self.client.get(
            self.url,
            {
                "response_type": "code",
                "client_id": client.client_id,
                "redirect_uri": "https://example.com/callback",
                "state": "xyz",
            },
        )
        assert response.status_code == status.HTTP_302_FOUND
        assert "state=xyz" in response["Location"]

    def test_unauthenticated_rejected(self) -> None:
        client = OAuth2ClientFactory(tenant=self.membership.tenant)
        unauthenticated = APIClient()
        response = unauthenticated.get(
            self.url,
            {
                "response_type": "code",
                "client_id": client.client_id,
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_client_id_rejected(self) -> None:
        response = self.client.get(
            self.url,
            {"response_type": "code", "client_id": "nonexistent"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_redirect_uri_rejected(self) -> None:
        client = OAuth2ClientFactory(tenant=self.membership.tenant)
        response = self.client.get(
            self.url,
            {
                "response_type": "code",
                "client_id": client.client_id,
                "redirect_uri": "https://evil.com/callback",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_public_client_without_pkce_rejected(self) -> None:
        client = PublicOAuth2ClientFactory(tenant=self.membership.tenant)
        response = self.client.get(
            self.url,
            {
                "response_type": "code",
                "client_id": client.client_id,
                "redirect_uri": "https://example.com/callback",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_public_client_with_pkce_succeeds(self) -> None:
        client = PublicOAuth2ClientFactory(tenant=self.membership.tenant)
        response = self.client.get(
            self.url,
            {
                "response_type": "code",
                "client_id": client.client_id,
                "redirect_uri": "https://example.com/callback",
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
            },
        )
        assert response.status_code == status.HTTP_302_FOUND
