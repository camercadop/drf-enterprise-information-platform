import pytest
from rest_framework.exceptions import ValidationError

from apps.iam_oauth.serializers import (
    AuthorizationCodeGrantSerializer,
    ClientCredentialsGrantSerializer,
)
from tests.factories.iam_oauth import (
    AuthorizationCodeFactory,
    OAuth2ClientFactory,
    PublicOAuth2ClientFactory,
)


@pytest.mark.django_db
class TestAuthorizationCodeGrantSerializer:
    def test_valid(self) -> None:
        auth_code = AuthorizationCodeFactory()
        s = AuthorizationCodeGrantSerializer(
            data={
                "code": auth_code.code,
                "client_id": auth_code.client.client_id,
                "redirect_uri": auth_code.redirect_uri,
            }
        )
        assert s.is_valid(), s.errors

    def test_invalid_code(self) -> None:
        client = OAuth2ClientFactory()
        s = AuthorizationCodeGrantSerializer(
            data={"code": "nonexistent", "client_id": client.client_id}
        )
        assert not s.is_valid()

    def test_client_mismatch(self) -> None:
        auth_code = AuthorizationCodeFactory()
        other_client = OAuth2ClientFactory(tenant=auth_code.client.tenant)
        s = AuthorizationCodeGrantSerializer(
            data={"code": auth_code.code, "client_id": other_client.client_id}
        )
        assert not s.is_valid()

    def test_consumed_code_rejected(self) -> None:
        auth_code = AuthorizationCodeFactory(is_consumed=True)
        s = AuthorizationCodeGrantSerializer(
            data={
                "code": auth_code.code,
                "client_id": auth_code.client.client_id,
            }
        )
        assert not s.is_valid()


@pytest.mark.django_db
class TestClientCredentialsGrantSerializer:
    def test_valid(self) -> None:
        client = OAuth2ClientFactory(
            grant_types="client_credentials", scope="read write"
        )
        s = ClientCredentialsGrantSerializer(
            data={
                "client_id": client.client_id,
                "client_secret": client.client_secret,
                "scope": "read",
            }
        )
        assert s.is_valid(), s.errors

    def test_invalid_secret(self) -> None:
        client = OAuth2ClientFactory(grant_types="client_credentials")
        s = ClientCredentialsGrantSerializer(
            data={"client_id": client.client_id, "client_secret": "wrong"}
        )
        assert not s.is_valid()

    def test_public_client_rejected(self) -> None:
        client = PublicOAuth2ClientFactory(grant_types="client_credentials")
        s = ClientCredentialsGrantSerializer(
            data={"client_id": client.client_id, "client_secret": ""}
        )
        assert not s.is_valid()

    def test_scope_exceeds_allowed_rejected(self) -> None:
        client = OAuth2ClientFactory(
            grant_types="client_credentials", scope="read"
        )
        s = ClientCredentialsGrantSerializer(
            data={
                "client_id": client.client_id,
                "client_secret": client.client_secret,
                "scope": "read write",
            }
        )
        assert not s.is_valid()
