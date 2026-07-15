"""Tests for membership state transition guards (ADR-013 / V6).

Verifies that activate/deactivate actions validate current state before
applying the transition and return 409 Conflict when already in target state.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_roles.models import TenantRole
from apps.iam_users.models import TenantMembership
from tests.factories.tenants import TenantMembershipFactory
from tests.factories.users import UserFactory


@pytest.mark.django_db
class TestMembershipDeactivate:
    """Tests for POST /api/tenants/memberships/{id}/deactivate/."""

    def _url(self, membership: TenantMembership) -> str:
        return f"/api/tenants/memberships/{membership.pk}/deactivate/"

    def test_deactivate_active_membership(
        self, auth_client: APIClient, membership: TenantMembership, role: TenantRole
    ) -> None:
        """Deactivating an active membership succeeds with 204."""
        target = TenantMembershipFactory(
            tenant=membership.tenant, role=role, user=UserFactory(), is_active=True
        )
        response = auth_client.post(self._url(target))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        target.refresh_from_db()
        assert target.is_active is False

    def test_deactivate_already_inactive_returns_409(
        self, auth_client: APIClient, membership: TenantMembership, role: TenantRole
    ) -> None:
        """Deactivating an already-inactive membership returns 409 Conflict."""
        target = TenantMembershipFactory(
            tenant=membership.tenant, role=role, user=UserFactory(), is_active=False
        )
        response = auth_client.post(self._url(target))
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_deactivate_already_inactive_does_not_change_state(
        self, auth_client: APIClient, membership: TenantMembership, role: TenantRole
    ) -> None:
        """A rejected deactivation does not modify the membership."""
        target = TenantMembershipFactory(
            tenant=membership.tenant, role=role, user=UserFactory(), is_active=False
        )
        auth_client.post(self._url(target))
        target.refresh_from_db()
        assert target.is_active is False


@pytest.mark.django_db
class TestMembershipActivate:
    """Tests for POST /api/tenants/memberships/{id}/activate/."""

    def _url(self, membership: TenantMembership) -> str:
        return f"/api/tenants/memberships/{membership.pk}/activate/"

    def test_activate_inactive_membership(
        self, auth_client: APIClient, membership: TenantMembership, role: TenantRole
    ) -> None:
        """Activating an inactive membership succeeds with 204."""
        target = TenantMembershipFactory(
            tenant=membership.tenant, role=role, user=UserFactory(), is_active=False
        )
        response = auth_client.post(self._url(target))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        target.refresh_from_db()
        assert target.is_active is True

    def test_activate_already_active_returns_409(
        self, auth_client: APIClient, membership: TenantMembership, role: TenantRole
    ) -> None:
        """Activating an already-active membership returns 409 Conflict."""
        target = TenantMembershipFactory(
            tenant=membership.tenant, role=role, user=UserFactory(), is_active=True
        )
        response = auth_client.post(self._url(target))
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_activate_already_active_does_not_change_state(
        self, auth_client: APIClient, membership: TenantMembership, role: TenantRole
    ) -> None:
        """A rejected activation does not modify the membership."""
        target = TenantMembershipFactory(
            tenant=membership.tenant, role=role, user=UserFactory(), is_active=True
        )
        auth_client.post(self._url(target))
        target.refresh_from_db()
        assert target.is_active is True
