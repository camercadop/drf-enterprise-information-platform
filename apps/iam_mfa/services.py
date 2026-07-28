import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from django.conf import settings
from rest_framework import serializers

logger = logging.getLogger(__name__)

_CHALLENGE_TTL_MINUTES = 5
_CHALLENGE_TYPE = "mfa_challenge"


def issue_challenge_token(user_id: str, tenant_id: str) -> str:
    """Issue a short-lived signed JWT representing a pending MFA challenge.

    The token is not an access token and cannot be used to authenticate requests.
    It carries a `type` claim set to `mfa_challenge` to distinguish it from real tokens.

    Args:
        user_id: The UUID string of the authenticated-but-not-yet-MFA-verified user.
        tenant_id: The UUID string of the resolved tenant.

    Returns:
        A signed JWT string valid for 5 minutes.
    """
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "type": _CHALLENGE_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=_CHALLENGE_TTL_MINUTES),
    }
    return str(jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256"))


def verify_challenge_token(token: str) -> dict[str, str]:
    """Verify and decode an MFA challenge token.

    Validates the signature, expiry, and `type` claim. Raises a DRF
    ValidationError on any failure so callers can raise_exception directly.

    Args:
        token: The challenge JWT string issued by issue_challenge_token.

    Returns:
        A dict with `user_id` and `tenant_id` string values.

    Raises:
        serializers.ValidationError: If the token is invalid, expired, or not
            an MFA challenge token.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError as err:
        logger.warning("MFA challenge token expired")
        raise serializers.ValidationError(
            {
                "challenge_token": [
                    serializers.ErrorDetail(
                        "Challenge token has expired.", code="mfa_challenge_expired"
                    )
                ]
            },
        ) from err
    except jwt.InvalidTokenError as err:
        logger.warning("MFA challenge token invalid")
        raise serializers.ValidationError(
            {
                "challenge_token": [
                    serializers.ErrorDetail(
                        "Invalid challenge token.", code="mfa_challenge_invalid"
                    )
                ]
            },
        ) from err

    if payload.get("type") != _CHALLENGE_TYPE:
        logger.warning("MFA challenge token has wrong type: %s", payload.get("type"))
        raise serializers.ValidationError(
            {
                "challenge_token": [
                    serializers.ErrorDetail(
                        "Invalid challenge token.", code="mfa_challenge_invalid"
                    )
                ]
            },
        )

    return {"user_id": payload["user_id"], "tenant_id": payload["tenant_id"]}
