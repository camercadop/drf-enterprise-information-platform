from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.iam_oauth.models import OAuth2RefreshToken
from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.iam_oauth import OAuth2ClientFactory, OAuth2RefreshTokenFactory
from tests.factories.users import UserFactory


class TestRevokeView(BaseActionAPITest):
    url = "/api/oauth/revoke/"

    @pytest.fixture(autouse=True)
    def _setup_base(self, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = APIClient()
        self.user = user
        self.membership = membership

    def _make_refresh_token_str(self, refresh_record: OAuth2RefreshToken) -> str:
        user = UserFactory()
        simplejwt_refresh = RefreshToken.for_user(user)
        simplejwt_refresh["jti"] = refresh_record.token
        return str(simplejwt_refresh)

    def test_valid_revocation_returns_200(self) -> None:
        oauth_client = OAuth2ClientFactory(tenant=self.membership.tenant)
        refresh_record = OAuth2RefreshTokenFactory(
            client=oauth_client,
            tenant=self.membership.tenant,
            expires_at=timezone.now() + timedelta(days=7),
        )
        token_str = self._make_refresh_token_str(refresh_record)
        response = self.client.post(
            self.url,
            {
                "token": token_str,
                "client_id": oauth_client.client_id,
                "client_secret": oauth_client.client_secret,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        refresh_record.refresh_from_db()
        assert refresh_record.is_revoked

    def test_revocation_marks_chain_revoked(self) -> None:
        oauth_client = OAuth2ClientFactory(tenant=self.membership.tenant)
        root = OAuth2RefreshTokenFactory(
            client=oauth_client,
            tenant=self.membership.tenant,
            expires_at=timezone.now() + timedelta(days=7),
        )
        child = OAuth2RefreshTokenFactory(
            client=oauth_client,
            tenant=self.membership.tenant,
            expires_at=timezone.now() + timedelta(days=7),
        )
        root.replaced_by = child
        root.save(update_fields=["replaced_by"])

        token_str = self._make_refresh_token_str(root)
        self.client.post(
            self.url,
            {
                "token": token_str,
                "client_id": oauth_client.client_id,
                "client_secret": oauth_client.client_secret,
            },
            format="json",
        )
        child.refresh_from_db()
        assert child.is_revoked

    def test_unknown_client_returns_200(self) -> None:
        response = self.client.post(
            self.url,
            {"token": "any", "client_id": "nonexistent"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_secret_returns_200(self) -> None:
        oauth_client = OAuth2ClientFactory(tenant=self.membership.tenant)
        response = self.client.post(
            self.url,
            {
                "token": "any",
                "client_id": oauth_client.client_id,
                "client_secret": "wrong",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_already_revoked_token_returns_200(self) -> None:
        oauth_client = OAuth2ClientFactory(tenant=self.membership.tenant)
        refresh_record = OAuth2RefreshTokenFactory(
            client=oauth_client,
            tenant=self.membership.tenant,
            is_revoked=True,
            expires_at=timezone.now() + timedelta(days=7),
        )
        token_str = self._make_refresh_token_str(refresh_record)
        response = self.client.post(
            self.url,
            {
                "token": token_str,
                "client_id": oauth_client.client_id,
                "client_secret": oauth_client.client_secret,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_missing_token_returns_200(self) -> None:
        oauth_client = OAuth2ClientFactory(tenant=self.membership.tenant)
        response = self.client.post(
            self.url,
            {"client_id": oauth_client.client_id},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
