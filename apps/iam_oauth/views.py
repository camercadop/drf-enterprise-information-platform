import logging
from typing import cast

from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.iam_oauth.models import OAuth2Client, OAuth2RefreshToken
from apps.iam_oauth.openapi import (
    OAuth2AuthorizeGetSchema,
    OAuth2AuthorizePostSchema,
    OAuth2RevokeSchema,
    OAuth2TokenSchema,
)
from apps.iam_oauth.serializers import (
    AuthorizationRequestSerializer,
    TokenRequestSerializer,
)
from apps.iam_oauth.services import revoke_refresh_token_chain
from apps.iam_oauth.settings import get_oauth2_setting
from apps.iam_oauth.signals import token_issued
from apps.sys_user_event.services import record_event
from apps.tenants.authentication import TenantJWTAuthentication
from apps.tenants.utils import get_tenant_id

logger = logging.getLogger(__name__)

User = get_user_model()


class AuthorizeView(APIView):
    """OAuth2 Authorization Code flow authorization endpoint.

    Handles the authorization request, validates the client and
    parameters, and issues an authorization code. Requires an
    authenticated user via TenantJWTAuthentication.
    """

    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _issue_code(
        self, request: Request, serializer: AuthorizationRequestSerializer
    ) -> Response | HttpResponseRedirect:
        redirect_uri = serializer.validated_data.get("redirect_uri", "")
        state = serializer.validated_data.get("state", "")

        tenant_id = get_tenant_id(request)
        if not tenant_id:
            return Response(
                {
                    "error": "invalid_request",
                    "error_description": "Tenant not resolved.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.tenant_id = tenant_id  # type: ignore[attr-defined]

        auth_code = serializer.save()

        redirect_url = f"{redirect_uri}?code={auth_code.code}"
        if state:
            redirect_url += f"&state={state}"

        return HttpResponseRedirect(redirect_url)

    @OAuth2AuthorizeGetSchema
    def get(self, request: Request) -> Response | HttpResponseRedirect:
        """Handle GET authorization request."""
        serializer = AuthorizationRequestSerializer(
            data=request.query_params, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return self._issue_code(request, serializer)

    @OAuth2AuthorizePostSchema
    def post(self, request: Request) -> Response | HttpResponseRedirect:
        serializer = AuthorizationRequestSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return self._issue_code(request, serializer)


class TokenView(APIView):
    """OAuth2 token endpoint.

    Handles authorization_code and client_credentials grant types.
    The endpoint is unauthenticated — client identity is established
    via client_id/client_secret in the request body.
    """

    permission_classes = [AllowAny]

    @OAuth2TokenSchema
    def post(self, request: Request) -> Response:
        """Handle token issuance request."""
        serializer = TokenRequestSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        token_data = serializer.save()

        grant_type = token_data.get("grant_type", "authorization_code")

        if grant_type == "client_credentials":
            return Response(
                {
                    "access_token": token_data["access_token"],
                    "token_type": "Bearer",
                    "expires_in": cast(
                        int, get_oauth2_setting("ACCESS_TOKEN_LIFETIME_MINUTES")
                    )
                    * 60,
                    "scope": token_data["scope"],
                },
                status=status.HTTP_200_OK,
            )

        tenant_id = token_data["tenant_id"]
        user_id = token_data["user_id"]
        scope = token_data["scope"]
        client_id = token_data["client_id"]

        if not user_id:
            return Response(
                {
                    "error": "invalid_grant",
                    "error_description": "Authorization code has no associated user.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {
                    "error": "invalid_grant",
                    "error_description": "User not found.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh_record = token_data.get("new_refresh_token") or token_data.get(
            "refresh_token_record"
        )

        refresh = RefreshToken.for_user(user)
        refresh["tenant_id"] = tenant_id
        refresh["scope"] = scope
        if refresh_record:
            refresh["jti"] = refresh_record.token

        access_token = refresh.access_token

        record_event(
            actor=None,
            user_email=user.email,
            category="oauth",
            event="token_issued",
            tenant_id=tenant_id,
            metadata={
                "client_id": client_id,
                "user_id": user_id,
                "grant_type": grant_type,
            },
        )

        token_issued.send(
            sender=TokenView,
            client_id=client_id,
            user_id=user_id,
            tenant_id=tenant_id,
            grant_type=grant_type,
        )

        return Response(
            {
                "access_token": str(access_token),
                "refresh_token": str(refresh),
                "token_type": "Bearer",
                "expires_in": cast(
                    int, get_oauth2_setting("ACCESS_TOKEN_LIFETIME_MINUTES")
                )  # type: ignore[arg-type]
                * 60,
            },
            status=status.HTTP_200_OK,
        )


class RevokeView(APIView):
    """OAuth2 token revocation endpoint (RFC 7009).

    Accepts a refresh token and revokes it along with its entire rotation
    chain. Always returns 200 OK per RFC 7009 — invalid or already-revoked
    tokens are silently accepted but logged as warnings.
    """

    permission_classes = [AllowAny]

    @OAuth2RevokeSchema
    def post(self, request: Request) -> Response:
        """Handle token revocation request."""
        token_str = request.data.get("token", "")
        client_id = request.data.get("client_id", "")
        client_secret = request.data.get("client_secret", "")

        if not token_str or not client_id:
            return Response(status=status.HTTP_200_OK)

        try:
            client = OAuth2Client.objects.get(client_id=client_id, is_active=True)
        except OAuth2Client.DoesNotExist:
            logger.warning("Revocation request for unknown client_id=%s", client_id)
            return Response(status=status.HTTP_200_OK)

        if client.is_confidential and client.client_secret != client_secret:
            logger.warning(
                "Revocation request with invalid client_secret client_id=%s", client_id
            )
            return Response(status=status.HTTP_200_OK)

        try:
            from rest_framework_simplejwt.tokens import (
                RefreshToken as SimpJWTRefreshToken,
            )

            decoded = SimpJWTRefreshToken(token_str)
            token_ref = decoded["jti"]
            record = OAuth2RefreshToken.objects.get(token=token_ref)
        except OAuth2RefreshToken.DoesNotExist:
            logger.warning(
                "Revocation request for unknown token client_id=%s", client_id
            )
            return Response(status=status.HTTP_200_OK)
        except Exception:
            logger.warning(
                "Revocation request with invalid token client_id=%s", client_id
            )
            return Response(status=status.HTTP_200_OK)

        if record.client != client:
            logger.warning(
                "Revocation request token/client mismatch client_id=%s", client_id
            )
            return Response(status=status.HTTP_200_OK)

        if record.is_revoked:
            logger.warning(
                "Revocation request for already-revoked token client_id=%s", client_id
            )
            return Response(status=status.HTTP_200_OK)

        revoke_refresh_token_chain(record)

        record_event(
            actor=None,
            user_email="",
            category="oauth",
            event="token_revoked",
            tenant_id=str(record.tenant_id),
            metadata={
                "client_id": client_id,
                "user_id": str(record.user_id),
            },
        )

        logger.info(
            "Refresh token chain revoked client_id=%s user_id=%s",
            client_id,
            record.user_id,
        )

        return Response(status=status.HTTP_200_OK)
