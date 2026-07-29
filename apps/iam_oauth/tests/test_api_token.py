import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.iam_oauth import (
    AuthorizationCodeFactory,
    OAuth2ClientFactory,
    OAuth2RefreshTokenFactory,
)
from tests.factories.users import UserFactory


class TestTokenView(BaseActionAPITest):
    url = "/api/oauth/token/"

    @pytest.fixture(autouse=True)
    def _setup_base(self, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = APIClient()
        self.user = user
        self.membership = membership

    # --- authorization_code grant ---

    def test_authorization_code_issues_tokens(self) -> None:
        user = UserFactory()
        oauth_client = OAuth2ClientFactory(tenant=self.membership.tenant)
        auth_code = AuthorizationCodeFactory(
            client=oauth_client,
            tenant=self.membership.tenant,
            user_id=user.pk,
            redirect_uri="https://example.com/callback",
        )
        response = self.client.post(
            self.url,
            {
                "grant_type": "authorization_code",
                "code": auth_code.code,
                "client_id": oauth_client.client_id,
                "redirect_uri": "https://example.com/callback",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

    def test_authorization_code_consumed_twice_rejected(self) -> None:
        user = UserFactory()
        oauth_client = OAuth2ClientFactory(tenant=self.membership.tenant)
        auth_code = AuthorizationCodeFactory(
            client=oauth_client,
            tenant=self.membership.tenant,
            user_id=user.pk,
        )
        payload = {
            "grant_type": "authorization_code",
            "code": auth_code.code,
            "client_id": oauth_client.client_id,
        }
        self.client.post(self.url, payload, format="json")
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_authorization_code_invalid_code_rejected(self) -> None:
        oauth_client = OAuth2ClientFactory(tenant=self.membership.tenant)
        response = self.client.post(
            self.url,
            {
                "grant_type": "authorization_code",
                "code": "invalid",
                "client_id": oauth_client.client_id,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # --- client_credentials grant ---

    def test_client_credentials_issues_access_token(self) -> None:
        oauth_client = OAuth2ClientFactory(
            tenant=self.membership.tenant,
            grant_types="client_credentials",
            scope="read",
        )
        response = self.client.post(
            self.url,
            {
                "grant_type": "client_credentials",
                "client_id": oauth_client.client_id,
                "client_secret": oauth_client.client_secret,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "access_token" in data
        assert "refresh_token" not in data
        assert data["token_type"] == "Bearer"

    def test_client_credentials_invalid_secret_rejected(self) -> None:
        oauth_client = OAuth2ClientFactory(
            tenant=self.membership.tenant,
            grant_types="client_credentials",
        )
        response = self.client.post(
            self.url,
            {
                "grant_type": "client_credentials",
                "client_id": oauth_client.client_id,
                "client_secret": "wrong",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # --- refresh_token grant ---

    def test_refresh_token_rotates_and_issues_new_pair(self) -> None:
        from datetime import timedelta

        from django.utils import timezone
        from rest_framework_simplejwt.tokens import RefreshToken

        user = UserFactory()
        oauth_client = OAuth2ClientFactory(
            tenant=self.membership.tenant,
            grant_types="authorization_code,refresh_token",
        )
        refresh_record = OAuth2RefreshTokenFactory(
            client=oauth_client,
            tenant=self.membership.tenant,
            user_id=user.pk,
            expires_at=timezone.now() + timedelta(days=7),
        )
        simplejwt_refresh = RefreshToken.for_user(user)
        simplejwt_refresh["jti"] = refresh_record.token

        response = self.client.post(
            self.url,
            {
                "grant_type": "refresh_token",
                "refresh_token": str(simplejwt_refresh),
                "client_id": oauth_client.client_id,
                "client_secret": oauth_client.client_secret,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data

    def test_revoked_refresh_token_rejected(self) -> None:
        from datetime import timedelta

        from django.utils import timezone
        from rest_framework_simplejwt.tokens import RefreshToken

        user = UserFactory()
        oauth_client = OAuth2ClientFactory(
            tenant=self.membership.tenant,
            grant_types="authorization_code,refresh_token",
        )
        refresh_record = OAuth2RefreshTokenFactory(
            client=oauth_client,
            tenant=self.membership.tenant,
            user_id=user.pk,
            is_revoked=True,
            expires_at=timezone.now() + timedelta(days=7),
        )
        simplejwt_refresh = RefreshToken.for_user(user)
        simplejwt_refresh["jti"] = refresh_record.token

        response = self.client.post(
            self.url,
            {
                "grant_type": "refresh_token",
                "refresh_token": str(simplejwt_refresh),
                "client_id": oauth_client.client_id,
                "client_secret": oauth_client.client_secret,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # --- unsupported grant type ---

    def test_unsupported_grant_type_rejected(self) -> None:
        response = self.client.post(
            self.url,
            {"grant_type": "implicit", "client_id": "any"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
