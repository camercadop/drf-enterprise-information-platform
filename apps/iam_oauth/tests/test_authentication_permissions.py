"""Tests for apps.iam_oauth.authentication and permissions."""

import base64
from unittest.mock import MagicMock

import pytest
from rest_framework.exceptions import AuthenticationFailed

from apps.iam_oauth.authentication import OAuth2ClientAuthentication
from apps.iam_oauth.permissions import IsOAuth2Client, IsOwnerOrConfidentialClient
from tests.factories.iam_oauth import OAuth2ClientFactory, PublicOAuth2ClientFactory


def _make_request(
    auth_header: str | None = None,
    body: dict | None = None,
) -> MagicMock:
    request = MagicMock()
    request.META = {}
    if auth_header:
        request.META["HTTP_AUTHORIZATION"] = auth_header
    request.data = body or {}
    request.POST = body or {}
    return request


def _basic_header(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    return f"Basic {credentials}"


@pytest.mark.django_db
class TestOAuth2ClientAuthentication:
    def test_returns_none_when_no_credentials(self) -> None:
        auth = OAuth2ClientAuthentication()
        request = _make_request()
        assert auth.authenticate(request) is None

    def test_authenticates_via_basic_auth(self) -> None:
        client = OAuth2ClientFactory()
        auth = OAuth2ClientAuthentication()
        request = _make_request(auth_header=_basic_header(client.client_id, client.client_secret))

        result = auth.authenticate(request)

        assert result is not None
        assert result[0] == client
        assert result[1] is None

    def test_authenticates_via_body_params(self) -> None:
        client = OAuth2ClientFactory()
        auth = OAuth2ClientAuthentication()
        request = _make_request(body={"client_id": client.client_id, "client_secret": client.client_secret})

        result = auth.authenticate(request)

        assert result is not None
        assert result[0] == client

    def test_raises_when_client_id_not_found(self) -> None:
        auth = OAuth2ClientAuthentication()
        request = _make_request(body={"client_id": "nonexistent", "client_secret": "x"})

        with pytest.raises(AuthenticationFailed, match="Invalid client_id"):
            auth.authenticate(request)

    def test_raises_when_client_inactive(self) -> None:
        client = OAuth2ClientFactory(is_active=False)
        auth = OAuth2ClientAuthentication()
        request = _make_request(body={"client_id": client.client_id, "client_secret": client.client_secret})

        with pytest.raises(AuthenticationFailed, match="inactive"):
            auth.authenticate(request)

    def test_raises_when_confidential_client_wrong_secret(self) -> None:
        client = OAuth2ClientFactory(is_confidential=True)
        auth = OAuth2ClientAuthentication()
        request = _make_request(body={"client_id": client.client_id, "client_secret": "wrong"})

        with pytest.raises(AuthenticationFailed, match="Invalid client_secret"):
            auth.authenticate(request)

    def test_public_client_authenticates_without_secret(self) -> None:
        client = PublicOAuth2ClientFactory()
        auth = OAuth2ClientAuthentication()
        request = _make_request(body={"client_id": client.client_id})

        result = auth.authenticate(request)

        assert result is not None
        assert result[0] == client

    def test_returns_none_on_malformed_basic_auth(self) -> None:
        auth = OAuth2ClientAuthentication()
        request = _make_request(auth_header="Basic !!!invalid!!!")

        result = auth.authenticate(request)

        assert result is None

    def test_authenticate_header_returns_basic_realm(self) -> None:
        auth = OAuth2ClientAuthentication()
        assert "Basic" in auth.authenticate_header(MagicMock())


@pytest.mark.django_db
class TestIsOAuth2Client:
    def test_returns_true_for_active_client(self) -> None:
        client = OAuth2ClientFactory()
        permission = IsOAuth2Client()
        request = MagicMock()
        request.data = {"client_id": client.client_id}
        request.query_params = {}

        assert permission.has_permission(request, MagicMock()) is True
        assert request.iam_oauth_client == client

    def test_returns_false_when_no_client_id(self) -> None:
        permission = IsOAuth2Client()
        request = MagicMock()
        request.data = {}
        request.query_params = {}

        assert permission.has_permission(request, MagicMock()) is False

    def test_returns_false_when_client_not_found(self) -> None:
        permission = IsOAuth2Client()
        request = MagicMock()
        request.data = {"client_id": "nonexistent"}
        request.query_params = {}

        assert permission.has_permission(request, MagicMock()) is False

    def test_returns_false_when_client_inactive(self) -> None:
        client = OAuth2ClientFactory(is_active=False)
        permission = IsOAuth2Client()
        request = MagicMock()
        request.data = {"client_id": client.client_id}
        request.query_params = {}

        assert permission.has_permission(request, MagicMock()) is False


@pytest.mark.django_db
class TestIsOwnerOrConfidentialClient:
    def test_returns_false_when_no_client_on_request(self) -> None:
        permission = IsOwnerOrConfidentialClient()
        request = MagicMock(spec=[])

        assert permission.has_permission(request, MagicMock()) is False

    def test_returns_true_for_confidential_client(self) -> None:
        client = OAuth2ClientFactory(is_confidential=True)
        permission = IsOwnerOrConfidentialClient()
        request = MagicMock()
        request.iam_oauth_client = client

        assert permission.has_permission(request, MagicMock()) is True

    def test_returns_true_for_public_client(self) -> None:
        client = PublicOAuth2ClientFactory()
        permission = IsOwnerOrConfidentialClient()
        request = MagicMock()
        request.iam_oauth_client = client

        assert permission.has_permission(request, MagicMock()) is True
