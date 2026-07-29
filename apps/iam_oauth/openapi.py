"""OpenAPI schema decorators for the iam_oauth endpoints."""

from drf_spectacular.utils import OpenApiResponse, extend_schema

_AUTHORIZE_SUMMARY = "OAuth2 authorization endpoint"
_AUTHORIZE_DESCRIPTION = (
    "Validates the authorization request and issues an authorization code, "
    "redirecting to the registered redirect_uri. Requires a valid user Bearer token."
)
_AUTHORIZE_RESPONSES = {
    302: OpenApiResponse(description="Redirect to redirect_uri with authorization code"),
    400: OpenApiResponse(description="Invalid request"),
}

OAuth2AuthorizeGetSchema = extend_schema(
    operation_id="oauth2_authorize_get",
    summary=_AUTHORIZE_SUMMARY,
    description=_AUTHORIZE_DESCRIPTION,
    tags=["OAuth2"],
    request=None,
    responses=_AUTHORIZE_RESPONSES,
)

OAuth2AuthorizePostSchema = extend_schema(
    operation_id="oauth2_authorize_post",
    summary=_AUTHORIZE_SUMMARY,
    description=_AUTHORIZE_DESCRIPTION,
    tags=["OAuth2"],
    request=None,
    responses=_AUTHORIZE_RESPONSES,
)

OAuth2TokenSchema = extend_schema(
    operation_id="oauth2_token",
    summary="OAuth2 token endpoint",
    description=(
        "Issues access and refresh tokens for `authorization_code` and `refresh_token` "
        "grant types, or an access token for `client_credentials`. "
        "Client identity is established via `client_id`/`client_secret` in the request body."
    ),
    auth=[],
    request={
        "application/x-www-form-urlencoded": {
            "type": "object",
            "properties": {
                "grant_type": {
                    "type": "string",
                    "enum": [
                        "authorization_code",
                        "client_credentials",
                        "refresh_token",
                    ],
                },
                "code": {"type": "string"},
                "client_id": {"type": "string"},
                "client_secret": {"type": "string"},
                "redirect_uri": {"type": "string", "format": "uri"},
                "code_verifier": {"type": "string"},
                "refresh_token": {"type": "string"},
                "scope": {"type": "string"},
            },
            "required": ["grant_type", "client_id"],
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "access_token": {"type": "string"},
                "refresh_token": {"type": "string"},
                "token_type": {"type": "string", "enum": ["Bearer"]},
                "expires_in": {"type": "integer"},
                "scope": {"type": "string"},
            },
        }
    },
    tags=["OAuth2"],
)

OAuth2RevokeSchema = extend_schema(
    operation_id="oauth2_revoke",
    summary="OAuth2 token revocation (RFC 7009)",
    description=(
        "Revokes a refresh token and its entire rotation chain. "
        "Always returns 200 OK regardless of token validity per RFC 7009."
    ),
    auth=[],
    request={
        "application/x-www-form-urlencoded": {
            "type": "object",
            "properties": {
                "token": {"type": "string"},
                "client_id": {"type": "string"},
                "client_secret": {"type": "string"},
            },
            "required": ["token", "client_id"],
        }
    },
    responses={200: None},
    tags=["OAuth2"],
)
