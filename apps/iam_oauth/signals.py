import logging

from django.dispatch import Signal, receiver

logger = logging.getLogger(__name__)

authorization_code_issued = Signal()
# Sent when an authorization code is issued.
# Provides: client_id (str), user_id (str), tenant_id (str), scope (str)

authorization_code_consumed = Signal()
# Sent when an authorization code is consumed.
# Provides: client_id (str), user_id (str), tenant_id (str)

token_issued = Signal()
# Sent when an OAuth2 token is issued.
# Provides: client_id (str), user_id (str), tenant_id (str), grant_type (str)

token_revoked = Signal()
# Sent when an OAuth2 token is revoked.
# Provides: client_id (str), user_id (str), tenant_id (str)


@receiver(authorization_code_issued)
def handle_authorization_code_issued(
    sender: object,
    client_id: str,
    user_id: str,
    tenant_id: str,
    scope: str,
    **kwargs: object,
) -> None:
    """Log authorization code issuance."""
    logger.info(
        "Authorization code issued client_id=%s user_id=%s tenant_id=%s scope=%s",
        client_id,
        user_id,
        tenant_id,
        scope,
    )


@receiver(authorization_code_consumed)
def handle_authorization_code_consumed(
    sender: object, client_id: str, user_id: str, tenant_id: str, **kwargs: object
) -> None:
    """Log authorization code consumption."""
    logger.info(
        "Authorization code consumed client_id=%s user_id=%s tenant_id=%s",
        client_id,
        user_id,
        tenant_id,
    )


@receiver(token_issued)
def handle_token_issued(
    sender: object,
    client_id: str,
    user_id: str,
    tenant_id: str,
    grant_type: str,
    **kwargs: object,
) -> None:
    """Log token issuance."""
    logger.info(
        "OAuth2 token issued client_id=%s user_id=%s tenant_id=%s grant_type=%s",
        client_id,
        user_id,
        tenant_id,
        grant_type,
    )


@receiver(token_revoked)
def handle_token_revoked(
    sender: object, client_id: str, user_id: str, tenant_id: str, **kwargs: object
) -> None:
    """Log token revocation."""
    logger.info(
        "OAuth2 token revoked client_id=%s user_id=%s tenant_id=%s",
        client_id,
        user_id,
        tenant_id,
    )
