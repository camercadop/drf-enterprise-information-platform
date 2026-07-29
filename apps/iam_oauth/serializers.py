import logging
from typing import cast

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.iam_oauth.models import AuthorizationCode, OAuth2Client
from apps.iam_oauth.services import (
    consume_authorization_code,
    consume_refresh_token,
    generate_authorization_code,
    issue_client_credentials_token,
)
from apps.tenants.utils import get_tenant_id

logger = logging.getLogger(__name__)


class AuthorizationRequestSerializer(serializers.Serializer):
    """Validates the OAuth2 authorization request parameters."""

    response_type = serializers.CharField()
    client_id = serializers.CharField()
    redirect_uri = serializers.URLField(required=False, allow_blank=True)
    scope = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    code_challenge = serializers.CharField(required=False, allow_blank=True)
    code_challenge_method = serializers.CharField(required=False, allow_blank=True)

    def validate_client_id(self, value: str) -> str:
        try:
            OAuth2Client.objects.get(client_id=value, is_active=True)
        except OAuth2Client.DoesNotExist as err:
            raise ValidationError("Invalid client_id.") from err
        return value

    def validate(self, attrs: dict) -> dict:
        client_id = attrs.get("client_id")
        try:
            client = OAuth2Client.objects.get(client_id=client_id, is_active=True)
        except OAuth2Client.DoesNotExist as err:
            raise ValidationError("Invalid client_id.") from err

        if client.response_type_list and "code" not in client.response_type_list:
            raise ValidationError(
                "This client does not support the authorization code flow."
            )

        redirect_uri = attrs.get("redirect_uri", "")
        if redirect_uri and redirect_uri not in client.redirect_uri_list:
            raise ValidationError("Invalid redirect_uri.")

        if not redirect_uri and client.redirect_uri_list:
            redirect_uri = client.redirect_uri_list[0]

        if not client.is_confidential:
            code_challenge = attrs.get("code_challenge", "")
            if not code_challenge:
                raise ValidationError("PKCE code_challenge is required for public clients.")
            code_challenge_method = attrs.get("code_challenge_method", "")
            if code_challenge_method not in ("S256", "plain"):
                raise ValidationError("code_challenge_method must be S256 or plain.")

        attrs["client"] = client
        attrs["redirect_uri"] = redirect_uri
        return attrs

    def save(self, **kwargs: object) -> AuthorizationCode:
        """Generates an authorization code for the validated request."""
        client = self.validated_data["client"]
        tenant_id = get_tenant_id(self.context["request"]) or ""
        redirect_uri = self.validated_data.get("redirect_uri", "")
        scope = self.validated_data.get("scope", "")
        code_challenge = self.validated_data.get("code_challenge", "")
        code_challenge_method = self.validated_data.get("code_challenge_method", "")
        user_id = (
            str(self.context["request"].user.pk)
            if self.context["request"].user
            and self.context["request"].user.is_authenticated
            else ""
        )

        return generate_authorization_code(
            client=client,
            tenant_id=tenant_id,
            redirect_uri=redirect_uri,
            scope=scope,
            user_id=user_id,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )


class AuthorizationCodeGrantSerializer(serializers.Serializer):
    """Validates and processes the authorization_code grant type."""

    code = serializers.CharField()
    client_id = serializers.CharField()
    redirect_uri = serializers.URLField(required=False, allow_blank=True)
    code_verifier = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        code = attrs.get("code", "")
        client_id = attrs.get("client_id", "")
        redirect_uri = attrs.get("redirect_uri", "")

        try:
            auth_code = AuthorizationCode.objects.get(code=code)
        except AuthorizationCode.DoesNotExist as err:
            raise ValidationError("Invalid authorization code.") from err

        if auth_code.is_consumed:
            raise ValidationError("Authorization code already consumed.")

        client = auth_code.client
        if client.client_id != client_id:
            raise ValidationError("client_id does not match the authorization code.")

        if redirect_uri and redirect_uri != auth_code.redirect_uri:
            raise ValidationError("redirect_uri does not match the authorization code.")

        attrs["client"] = client
        attrs["auth_code"] = auth_code
        attrs["redirect_uri"] = redirect_uri or auth_code.redirect_uri
        return attrs

    def save(self, **kwargs: object) -> dict:
        """Consumes the authorization code and returns token data."""
        client = self.validated_data["client"]
        auth_code = self.validated_data["auth_code"]
        redirect_uri = self.validated_data.get("redirect_uri", "")
        code_verifier = self.validated_data.get("code_verifier", "")

        return consume_authorization_code(
            code=auth_code.code,
            client=client,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )


class ClientCredentialsGrantSerializer(serializers.Serializer):
    """Validates and processes the client_credentials grant type."""

    client_id = serializers.CharField()
    client_secret = serializers.CharField()
    scope = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        client_id = attrs.get("client_id", "")
        client_secret = attrs.get("client_secret", "")

        try:
            client = OAuth2Client.objects.get(client_id=client_id, is_active=True)
        except OAuth2Client.DoesNotExist as err:
            raise ValidationError("Invalid client_id.") from err

        if not client.is_confidential:
            raise ValidationError("client_credentials grant requires a confidential client.")

        if client.client_secret != client_secret:
            raise ValidationError("Invalid client_secret.")

        if "client_credentials" not in client.grant_type_list:
            raise ValidationError("This client does not support the client_credentials grant.")

        scope = attrs.get("scope", "") or client.scope
        requested_scopes = set(scope.split())
        allowed_scopes = set(client.scope_list)
        if not requested_scopes.issubset(allowed_scopes):
            raise ValidationError("Requested scope exceeds client allowed scope.")

        attrs["client"] = client
        attrs["scope"] = scope
        return attrs

    def save(self, **kwargs: object) -> dict:
        """Issues a client credentials token and returns token data."""
        client = self.validated_data["client"]
        scope = self.validated_data.get("scope", "")
        return issue_client_credentials_token(client=client, scope=scope)


class RefreshTokenGrantSerializer(serializers.Serializer):
    """Validates and processes the refresh_token grant type."""

    refresh_token = serializers.CharField()
    client_id = serializers.CharField()
    client_secret = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        client_id = attrs.get("client_id", "")
        client_secret = attrs.get("client_secret", "")

        try:
            client = OAuth2Client.objects.get(client_id=client_id, is_active=True)
        except OAuth2Client.DoesNotExist as err:
            raise ValidationError("Invalid client_id.") from err

        if client.is_confidential and client.client_secret != client_secret:
            raise ValidationError("Invalid client_secret.")

        if "refresh_token" not in client.grant_type_list:
            raise ValidationError("This client does not support the refresh_token grant.")

        attrs["client"] = client
        return attrs

    def save(self, **kwargs: object) -> dict:
        """Rotates the refresh token and returns token data."""
        from rest_framework_simplejwt.tokens import RefreshToken as SimpJWTRefreshToken

        token_str = self.validated_data["refresh_token"]
        client = self.validated_data["client"]
        scope = self.validated_data.get("scope", "")

        try:
            decoded = SimpJWTRefreshToken(token_str)
            token_ref = decoded["jti"]
        except Exception as err:
            raise ValidationError("Invalid refresh token.") from err

        return consume_refresh_token(
            token_ref=token_ref,
            client=client,
            scope=scope,
        )


class TokenRequestSerializer(serializers.Serializer):
    """Dispatches token requests to the appropriate grant type serializer."""

    grant_type = serializers.CharField()

    SUPPORTED_GRANT_TYPES = {
        "authorization_code": AuthorizationCodeGrantSerializer,
        "client_credentials": ClientCredentialsGrantSerializer,
        "refresh_token": RefreshTokenGrantSerializer,
    }

    def validate(self, attrs: dict) -> dict:
        grant_type = attrs.get("grant_type", "")
        serializer_class = self.SUPPORTED_GRANT_TYPES.get(grant_type)
        if not serializer_class:
            raise ValidationError(
                f"Unsupported grant_type. Supported: {', '.join(self.SUPPORTED_GRANT_TYPES)}"
            )
        grant_serializer = cast(
            serializers.Serializer,
            serializer_class(data=self.initial_data, context=self.context),
        )
        grant_serializer.is_valid(raise_exception=True)
        attrs["_grant_serializer"] = grant_serializer
        return attrs

    def save(self, **kwargs: object) -> dict:
        """Delegates token issuance to the resolved grant serializer."""
        result: dict = self.validated_data["_grant_serializer"].save()
        return result
