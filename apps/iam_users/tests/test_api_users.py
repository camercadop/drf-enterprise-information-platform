"""Tests for the iam_users API endpoints."""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_users.models import TenantMembership, User
from tests.base import BaseListAPITest, BaseRetrieveAPITest
from tests.factories.tenants import TenantMembershipFactory, TenantFactory
from tests.factories.users import UserFactory


class TestUserViewSet(BaseListAPITest, BaseRetrieveAPITest):
    """Tests for GET /api/iam/users/ and GET /api/iam/users/<pk>/."""

    url = "/api/iam/users/"

    def create_instance(self) -> User:
        """Create a user in the same tenant as the authenticated user."""
        return TenantMembershipFactory(tenant=self.membership.tenant).user


@pytest.mark.django_db
class TestUserViewSetScoping:
    """Tests for tenant-scoped queryset filtering."""

    def test_non_superuser_sees_only_tenant_members(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Users in the same tenant are visible; users in other tenants are not."""
        same_tenant_user = TenantMembershipFactory(tenant=membership.tenant).user
        other_tenant_user = TenantMembershipFactory().user

        response = auth_client.get("/api/iam/users/")

        assert response.status_code == status.HTTP_200_OK
        ids = [u["id"] for u in response.json()["data"]["results"]]
        assert str(same_tenant_user.pk) in ids
        assert str(other_tenant_user.pk) not in ids

    def test_superuser_sees_all_users(
        self, superuser_client: APIClient, superuser_membership: TenantMembership
    ) -> None:
        """Superusers are not scoped to a tenant and see every user."""
        user_a = TenantMembershipFactory().user
        user_b = TenantMembershipFactory().user

        response = superuser_client.get("/api/iam/users/")

        assert response.status_code == status.HTTP_200_OK
        ids = [u["id"] for u in response.json()["data"]["results"]]
        assert str(user_a.pk) in ids
        assert str(user_b.pk) in ids

    def test_unauthenticated_request_is_rejected(self, api_client: APIClient) -> None:
        """Unauthenticated requests to the user list return 401."""
        response = api_client.get("/api/iam/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_membership_user_is_excluded(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Users with inactive memberships in the tenant are not returned."""
        inactive = TenantMembershipFactory(tenant=membership.tenant, is_active=False).user

        response = auth_client.get("/api/iam/users/")

        ids = [u["id"] for u in response.json()["data"]["results"]]
        assert str(inactive.pk) not in ids


@pytest.mark.django_db
class TestUserMeEndpoint:
    """Tests for GET /api/iam/users/me/ and PATCH /api/iam/users/me/."""

    def test_get_me_returns_own_data(
        self, auth_client: APIClient, user: User
    ) -> None:
        """GET /me/ returns the authenticated user's own profile."""
        response = auth_client.get("/api/iam/users/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == str(user.pk)
        assert response.json()["data"]["email"] == user.email

    def test_patch_me_updates_name(
        self, auth_client: APIClient, user: User
    ) -> None:
        """PATCH /me/ with first_name and last_name updates the user."""
        response = auth_client.patch(
            "/api/iam/users/me/",
            {"first_name": "Updated", "last_name": "Name"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["first_name"] == "Updated"
        assert response.json()["data"]["last_name"] == "Name"
        user.refresh_from_db()
        assert user.first_name == "Updated"

    def test_patch_me_updates_personal_info(
        self, auth_client: APIClient, user: User
    ) -> None:
        """PATCH /me/ with personal_info creates or updates the user profile."""
        payload: dict[str, Any] = {"personal_info": {"phone": "555-0100"}}
        response = auth_client.patch("/api/iam/users/me/", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["personal_info"] == {"phone": "555-0100"}

    def test_patch_me_email_is_ignored(
        self, auth_client: APIClient, user: User
    ) -> None:
        """Email cannot be changed via PATCH /me/ — it is silently excluded."""
        original_email = user.email
        auth_client.patch(
            "/api/iam/users/me/", {"email": "hacked@example.com"}, format="json"
        )

        user.refresh_from_db()
        assert user.email == original_email

    def test_unauthenticated_me_is_rejected(self, api_client: APIClient) -> None:
        """Unauthenticated requests to /me/ return 401."""
        response = api_client.get("/api/iam/users/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
