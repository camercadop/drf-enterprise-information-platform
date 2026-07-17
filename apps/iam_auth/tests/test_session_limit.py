import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.iam_users.models import TenantMembership, User


LOGIN_URL = "/api/auth/login/"
LOGIN_PAYLOAD = {"email": None, "password": "TestPass123!"}


def _login(client: APIClient, email: str, tenant_id: str) -> None:
    client.post(LOGIN_URL, {"email": email, "password": "TestPass123!", "tenant_id": tenant_id})


@pytest.mark.django_db
class TestSessionConcurrencyLimit:
    @pytest.fixture(autouse=True)
    def _setup(self, api_client: APIClient, user: User, membership: TenantMembership) -> None:
        self.client = api_client
        self.user = user
        self.tenant_id = str(membership.tenant_id)

    def test_no_enforcement_when_limit_is_zero(self) -> None:
        """Sessions are not invalidated when MAX_CONCURRENT_SESSIONS is 0."""
        with patch("apps.iam_auth.serializers.settings") as mock_settings:
            mock_settings.AUTH_SESSION = {"MAX_CONCURRENT_SESSIONS": 0}
            _login(self.client, self.user.email, self.tenant_id)
            _login(self.client, self.user.email, self.tenant_id)
            _login(self.client, self.user.email, self.tenant_id)

        assert BlacklistedToken.objects.filter(token__user=self.user).count() == 0

    def test_oldest_session_blacklisted_when_limit_exceeded(self) -> None:
        """When limit is 1, logging in a second time blacklists the first session."""
        with patch("apps.iam_auth.serializers.settings") as mock_settings:
            mock_settings.AUTH_SESSION = {"MAX_CONCURRENT_SESSIONS": 1}
            _login(self.client, self.user.email, self.tenant_id)
            first_token = OutstandingToken.objects.filter(user=self.user).order_by("created_at").first()
            _login(self.client, self.user.email, self.tenant_id)

        assert BlacklistedToken.objects.filter(token=first_token).exists()

    def test_sessions_within_limit_are_not_blacklisted(self) -> None:
        """When active sessions are within the limit, the enforcer does not blacklist anything."""
        with patch("apps.iam_auth.serializers.settings") as mock_settings, \
             patch("apps.iam_auth.serializers.logger") as mock_logger:
            mock_settings.AUTH_SESSION = {"MAX_CONCURRENT_SESSIONS": 10}
            _login(self.client, self.user.email, self.tenant_id)
            _login(self.client, self.user.email, self.tenant_id)

        mock_logger.warning.assert_not_called()

    def test_multiple_excess_sessions_all_blacklisted(self) -> None:
        """When 3 sessions exist and limit is 1, the 2 oldest are blacklisted."""
        with patch("apps.iam_auth.serializers.settings") as mock_settings:
            mock_settings.AUTH_SESSION = {"MAX_CONCURRENT_SESSIONS": 1}
            _login(self.client, self.user.email, self.tenant_id)
            _login(self.client, self.user.email, self.tenant_id)
            oldest_two = list(
                OutstandingToken.objects.filter(user=self.user).order_by("created_at")[:2]
            )
            _login(self.client, self.user.email, self.tenant_id)

        blacklisted_ids = set(
            BlacklistedToken.objects.filter(token__user=self.user).values_list("token_id", flat=True)
        )
        for token in oldest_two:
            assert token.pk in blacklisted_ids

    def test_already_blacklisted_tokens_not_counted_as_active(self) -> None:
        """Pre-blacklisted tokens are excluded from the active session count."""
        refresh = RefreshToken.for_user(self.user)
        outstanding = OutstandingToken.objects.get(jti=refresh["jti"])
        BlacklistedToken.objects.create(token=outstanding)

        with patch("apps.iam_auth.serializers.settings") as mock_settings:
            mock_settings.AUTH_SESSION = {"MAX_CONCURRENT_SESSIONS": 1}
            _login(self.client, self.user.email, self.tenant_id)

        assert BlacklistedToken.objects.filter(token__user=self.user).count() == 1

    def test_session_limit_returns_200(self) -> None:
        """Login still succeeds (200) even when the session limit triggers eviction."""
        from apps.iam_auth.throttling import LoginEmailThrottle, LoginIPThrottle

        with patch("apps.iam_auth.serializers.settings") as mock_settings, \
             patch.object(LoginIPThrottle, "allow_request", return_value=True), \
             patch.object(LoginEmailThrottle, "allow_request", return_value=True):
            mock_settings.AUTH_SESSION = {"MAX_CONCURRENT_SESSIONS": 1}
            _login(self.client, self.user.email, self.tenant_id)
            response = self.client.post(
                LOGIN_URL,
                {"email": self.user.email, "password": "TestPass123!", "tenant_id": self.tenant_id},
            )

        assert response.status_code == status.HTTP_200_OK
