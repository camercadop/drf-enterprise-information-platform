import logging

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from apps.iam_oauth.models import OAuth2Client

logger = logging.getLogger(__name__)


class OAuth2ClientAuthentication(BaseAuthentication):
    """Authenticates OAuth2 clients using client_id and client_secret.

    Supports two authentication methods:
    1. HTTP Basic Auth (client_id:client_secret in Authorization header)
    2. Form-encoded body parameters (client_id and client_secret in POST body)
    """

    def authenticate(self, request: Request) -> tuple[OAuth2Client, None] | None:
        """Authenticate the OAuth2 client.

        Returns:
            A tuple of (client, None) if authentication succeeds,
            or None if no credentials are provided.

        Raises:
            AuthenticationFailed: If credentials are provided but invalid.
        """
        client_id, client_secret = self._get_credentials(request)

        if not client_id:
            return None

        try:
            client = OAuth2Client.objects.get(client_id=client_id)
        except OAuth2Client.DoesNotExist as err:
            raise AuthenticationFailed("Invalid client_id.") from err

        if not client.is_active:
            raise AuthenticationFailed("Client is inactive.")

        if client.is_confidential and client.client_secret:
            if client_secret != client.client_secret:
                raise AuthenticationFailed("Invalid client_secret.")

        return (client, None)

    def _get_credentials(self, request: Request) -> tuple[str | None, str | None]:
        """Extract client_id and client_secret from the request.

        Checks Authorization header first (HTTP Basic Auth),
        then falls back to POST body parameters.
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Basic "):
            import base64
            import binascii

            try:
                decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
                client_id, client_secret = decoded.split(":", 1)
                return client_id, client_secret
            except (ValueError, UnicodeDecodeError, binascii.Error):
                logger.warning("Failed to decode Basic Auth credentials")
                return None, None

        client_id = request.data.get("client_id") or request.POST.get("client_id")
        client_secret = request.data.get("client_secret") or request.POST.get(
            "client_secret"
        )

        return client_id, client_secret

    def authenticate_header(self, request: Request) -> str:
        return 'Basic realm="OAuth2"'
