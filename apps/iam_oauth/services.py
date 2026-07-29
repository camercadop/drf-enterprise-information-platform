import logging
import uuid
from datetime import timedelta
from typing import cast

from django.utils import timezone

from apps.iam_oauth.models import AuthorizationCode, OAuth2Client, OAuth2RefreshToken
from apps.iam_oauth.settings import get_oauth2_setting
from apps.iam_oauth.signals import (
    authorization_code_consumed,
    authorization_code_issued,
    token_issued,
    token_revoked,
)
from apps.sys_user_event.services import record_event

logger = logging.getLogger(__name__)


def generate_authorization_code(
    client: OAuth2Client,
    tenant_id: str,
    redirect_uri: str,
    scope: str,
    user_id: str,
    code_challenge: str = "",
    code_challenge_method: str = "",
) -> AuthorizationCode:
    """Generate and store an authorization code.

    Args:
        client: The OAuth2 client requesting the code.
        tenant_id: The tenant UUID string.
        redirect_uri: The redirect URI from the authorization request.
        scope: The granted scope string.
        user_id: The UUID of the authorizing user.
        code_challenge: PKCE code challenge (optional).
        code_challenge_method: PKCE code challenge method (optional).

    Returns:
        The created AuthorizationCode instance.
    """
    if not client.is_confidential and not code_challenge:
        from rest_framework.exceptions import ValidationError

        raise ValidationError("PKCE is required for public clients.")

    code_value = uuid.uuid4().hex[:32]
    lifetime = cast(int, get_oauth2_setting("AUTHORIZATION_CODE_LIFETIME"))

    auth_code: AuthorizationCode = AuthorizationCode.objects.create(
        client=client,
        tenant_id=tenant_id,
        code=code_value,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        user_id=user_id,
        expires_at=timezone.now() + timedelta(seconds=lifetime),
    )

    record_event(
        actor=None,
        user_email="",
        category="oauth",
        event="authorization_code_issued",
        tenant_id=tenant_id,
        metadata={
            "client_id": client.client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "user_id": user_id,
        },
    )

    logger.info(
        "Authorization code issued client_id=%s user_id=%s tenant_id=%s",
        client.client_id,
        user_id,
        tenant_id,
    )

    authorization_code_issued.send(
        sender=generate_authorization_code,
        client_id=client.client_id,
        user_id=user_id,
        tenant_id=tenant_id,
        scope=scope,
    )

    return auth_code


def revoke_refresh_token_chain(record: OAuth2RefreshToken) -> None:
    """Revoke a refresh token and its entire replacement chain.

    Walks the replaced_by lineage from the given record forward and marks
    every token as revoked. This ensures that if a stolen token was rotated
    by an attacker, all descendant tokens are also invalidated.

    Args:
        record: The OAuth2RefreshToken to start revocation from.
    """
    now = timezone.now()
    current: OAuth2RefreshToken | None = record
    while current is not None:
        if not current.is_revoked:
            current.is_revoked = True
            current.revoked_at = now
            current.save(update_fields=["is_revoked", "revoked_at"])
        try:
            current = current.replaced_by
        except OAuth2RefreshToken.DoesNotExist:
            current = None

    token_revoked.send(
        sender=revoke_refresh_token_chain,
        client_id=record.client.client_id,
        user_id=str(record.user_id),
        tenant_id=str(record.tenant_id),
    )


def issue_refresh_token(
    client: OAuth2Client,
    tenant_id: str,
    user_id: str,
    scope: str,
) -> OAuth2RefreshToken:
    """Create and persist an OAuth2RefreshToken record.

    Generates an opaque token reference stored as the JWT jti claim.
    The caller is responsible for embedding the record token into the JWT.

    Args:
        client: The OAuth2 client the token is issued to.
        tenant_id: The tenant UUID string.
        user_id: The UUID of the user the token is issued for.
        scope: The granted scope string.

    Returns:
        The created OAuth2RefreshToken instance.
    """
    lifetime_days = cast(int, get_oauth2_setting("REFRESH_TOKEN_LIFETIME_DAYS"))
    token_ref = uuid.uuid4().hex

    record: OAuth2RefreshToken = OAuth2RefreshToken.objects.create(
        client=client,
        tenant_id=tenant_id,
        user_id=user_id,
        token=token_ref,
        scope=scope,
        expires_at=timezone.now() + timedelta(days=lifetime_days),
    )
    return record


def consume_authorization_code(
    code: str,
    client: OAuth2Client,
    redirect_uri: str,
    code_verifier: str = "",
) -> dict:
    """Consume an authorization code and return token data.

    Validates the code, checks PKCE if applicable, marks the code
    as consumed, and returns the data needed to issue tokens.

    Args:
        code: The authorization code value.
        client: The OAuth2 client consuming the code.
        redirect_uri: The redirect URI from the token request.
        code_verifier: PKCE code verifier (optional).

    Returns:
        Dict with user_id, tenant_id, scope, client info, and refresh_token_record.

    Raises:
        ValidationError: If the code is invalid, consumed, expired, or PKCE fails.
    """
    from rest_framework.exceptions import ValidationError

    auth_code = AuthorizationCode.objects.get(code=code)

    if auth_code.is_consumed:
        raise ValidationError("Authorization code already consumed.")

    if timezone.now() > auth_code.expires_at:
        raise ValidationError("Authorization code has expired.")

    if auth_code.client != client:
        raise ValidationError("Client mismatch.")

    if redirect_uri and auth_code.redirect_uri != redirect_uri:
        raise ValidationError("redirect_uri mismatch.")

    if auth_code.code_challenge and code_verifier:
        _verify_pkce(code_verifier, auth_code)

    auth_code.is_consumed = True
    auth_code.consumed_at = timezone.now()
    auth_code.save(update_fields=["is_consumed", "consumed_at"])

    record_event(
        actor=None,
        user_email="",
        category="oauth",
        event="authorization_code_consumed",
        tenant_id=str(auth_code.tenant_id),
        metadata={
            "client_id": client.client_id,
            "user_id": str(auth_code.user_id) if auth_code.user_id else "",
        },
    )

    logger.info(
        "Authorization code consumed client_id=%s user_id=%s",
        client.client_id,
        auth_code.user_id,
    )

    authorization_code_consumed.send(
        sender=consume_authorization_code,
        client_id=client.client_id,
        user_id=str(auth_code.user_id) if auth_code.user_id else "",
        tenant_id=str(auth_code.tenant_id),
    )

    return {
        "user_id": str(auth_code.user_id) if auth_code.user_id else None,
        "tenant_id": str(auth_code.tenant_id),
        "scope": auth_code.scope,
        "client_id": client.client_id,
        "grant_type": "authorization_code",
        "refresh_token_record": issue_refresh_token(
            client=client,
            tenant_id=str(auth_code.tenant_id),
            user_id=str(auth_code.user_id) if auth_code.user_id else "",
            scope=auth_code.scope,
        ),
    }


def consume_refresh_token(
    token_ref: str,
    client: OAuth2Client,
    scope: str = "",
) -> dict:
    """Validate, rotate, and consume a refresh token.

    Marks the existing token as replaced, issues a new OAuth2RefreshToken,
    and returns the data needed to issue a new access token.

    Args:
        token_ref: The opaque token reference from the JWT jti claim.
        client: The OAuth2 client presenting the refresh token.
        scope: Requested scope; must be a subset of the original. Defaults to original scope.

    Returns:
        Dict with user_id, tenant_id, scope, client_id, grant_type, and new_refresh_token record.

    Raises:
        ValidationError: If the token is invalid, expired, revoked, or scope exceeds original.
    """
    from rest_framework.exceptions import ValidationError

    try:
        record = OAuth2RefreshToken.objects.get(token=token_ref)
    except OAuth2RefreshToken.DoesNotExist as err:
        raise ValidationError("Invalid refresh token.") from err

    if record.is_revoked:
        raise ValidationError("Refresh token has been revoked.")

    if timezone.now() > record.expires_at:
        raise ValidationError("Refresh token has expired.")

    if record.client != client:
        raise ValidationError("Client mismatch.")

    granted_scope = scope or record.scope
    requested_scopes = set(granted_scope.split())
    original_scopes = set(record.scope.split())
    if not requested_scopes.issubset(original_scopes):
        raise ValidationError("Requested scope exceeds the original granted scope.")

    new_record = issue_refresh_token(
        client=client,
        tenant_id=str(record.tenant_id),
        user_id=str(record.user_id),
        scope=granted_scope,
    )

    record.replaced_by = new_record
    record.is_revoked = True
    record.revoked_at = timezone.now()
    record.save(update_fields=["replaced_by", "is_revoked", "revoked_at"])

    logger.info(
        "Refresh token rotated client_id=%s user_id=%s tenant_id=%s",
        client.client_id,
        record.user_id,
        record.tenant_id,
    )

    token_issued.send(
        sender=consume_refresh_token,
        client_id=client.client_id,
        user_id=str(record.user_id),
        tenant_id=str(record.tenant_id),
        grant_type="refresh_token",
    )

    return {
        "user_id": str(record.user_id),
        "tenant_id": str(record.tenant_id),
        "scope": granted_scope,
        "client_id": client.client_id,
        "grant_type": "refresh_token",
        "new_refresh_token": new_record,
    }


def issue_client_credentials_token(client: OAuth2Client, scope: str) -> dict:
    """Issue a JWT access token for the client_credentials grant.

    Issues a short-lived access token with the client as the subject.
    No refresh token is issued — client credentials tokens are not renewable.

    Args:
        client: The authenticated confidential OAuth2 client.
        scope: The granted scope string.

    Returns:
        Dict with access_token, grant_type, tenant_id, scope, client_id, and user_id.
    """
    from rest_framework_simplejwt.tokens import AccessToken

    token = AccessToken()
    lifetime_minutes = cast(int, get_oauth2_setting("ACCESS_TOKEN_LIFETIME_MINUTES"))
    token.set_exp(lifetime=timedelta(minutes=lifetime_minutes))
    token["sub"] = client.client_id
    token["tenant_id"] = str(client.tenant_id)
    token["scope"] = scope
    token["token_type_hint"] = "client_credentials"

    record_event(
        actor=None,
        user_email="",
        category="oauth",
        event="token_issued",
        tenant_id=str(client.tenant_id),
        metadata={
            "client_id": client.client_id,
            "grant_type": "client_credentials",
            "scope": scope,
        },
    )

    logger.info(
        "Client credentials token issued client_id=%s tenant_id=%s",
        client.client_id,
        client.tenant_id,
    )

    token_issued.send(
        sender=issue_client_credentials_token,
        client_id=client.client_id,
        user_id="",
        tenant_id=str(client.tenant_id),
        grant_type="client_credentials",
    )

    return {
        "grant_type": "client_credentials",
        "access_token": str(token),
        "tenant_id": str(client.tenant_id),
        "scope": scope,
        "client_id": client.client_id,
        "user_id": None,
    }


def _verify_pkce(code_verifier: str, auth_code: AuthorizationCode) -> None:
    """Verify the PKCE code verifier against the stored code challenge.

    Args:
        code_verifier: The code verifier from the token request.
        auth_code: The authorization code with the stored challenge.

    Raises:
        ValidationError: If the PKCE verification fails.
    """
    import base64
    import hashlib

    challenge_method = auth_code.code_challenge_method or "plain"

    if challenge_method == "S256":
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    else:
        computed_challenge = code_verifier

    if computed_challenge != auth_code.code_challenge:
        from rest_framework.exceptions import ValidationError

        raise ValidationError("PKCE code verifier mismatch.")
