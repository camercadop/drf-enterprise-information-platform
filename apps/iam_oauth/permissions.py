import logging

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.iam_oauth.models import OAuth2Client

logger = logging.getLogger(__name__)


class IsOAuth2Client(BasePermission):
    """Permission that validates the OAuth2 client credentials."""

    def has_permission(self, request: Request, view: object) -> bool:
        client_id = request.data.get("client_id") or request.query_params.get(
            "client_id"
        )
        if not client_id:
            return False

        try:
            client = OAuth2Client.objects.get(client_id=client_id, is_active=True)
        except OAuth2Client.DoesNotExist:
            logger.warning("OAuth2 client not found: client_id=%s", client_id)
            return False

        request.iam_oauth_client = client
        return True


class IsOwnerOrConfidentialClient(BasePermission):
    """Permission that allows the client owner or confidential clients to proceed."""

    def has_permission(self, request: Request, view: object) -> bool:
        client = getattr(request, "iam_oauth_client", None)
        if not client:
            return False

        if client.is_confidential:
            return True

        return True
