import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.iam_users.models import TenantMembership, User


def _build_auth_client(user: User, membership: TenantMembership) -> APIClient:
    """Create an APIClient with a JWT containing the tenant_id claim."""
    token = AccessToken.for_user(user)
    token["tenant_id"] = str(membership.tenant_id)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture()
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture()
def auth_client(user: User, membership: TenantMembership) -> APIClient:
    return _build_auth_client(user, membership)


@pytest.fixture()
def superuser_client(
    superuser: User, superuser_membership: TenantMembership
) -> APIClient:
    return _build_auth_client(superuser, superuser_membership)
