"""Tests for TeamMembership endpoints."""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_teams.models import TeamMembership
from apps.iam_users.models import TenantMembership, User
from tests.factories.teams import TeamFactory, TeamMembershipFactory
from tests.factories.tenants import TenantMembershipFactory as MembershipFactory


@pytest.mark.django_db
class TestTeamMembershipList:
    """Tests for GET /api/teams/memberships/."""

    url = "/api/teams/memberships/"

    def test_list_returns_memberships_in_tenant(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Lists team memberships scoped to the user's tenant."""
        team = TeamFactory(tenant=membership.tenant)
        tm = TeamMembershipFactory(team=team, membership=membership)
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        ids = [r["id"] for r in response.data["results"]]
        assert str(tm.pk) in ids

    def test_list_excludes_other_tenant(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Does not return team memberships from other tenants."""
        TeamMembershipFactory()  # Different tenant
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestTeamMembershipCreate:
    """Tests for POST /api/teams/memberships/."""

    url = "/api/teams/memberships/"

    def test_add_member_to_team(
        self,
        superuser_client: APIClient,
        superuser_membership: TenantMembership,
    ) -> None:
        """Admin can add a tenant member to a team."""
        team = TeamFactory(tenant=superuser_membership.tenant)
        target = MembershipFactory(tenant=superuser_membership.tenant)
        response = superuser_client.post(
            self.url,
            {"team_id": str(team.pk), "membership_id": str(target.pk)},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert TeamMembership.objects.filter(
            team=team, membership=target
        ).exists()

    def test_duplicate_membership_returns_400(
        self,
        superuser_client: APIClient,
        superuser_membership: TenantMembership,
    ) -> None:
        """Cannot add the same member to a team twice."""
        team = TeamFactory(tenant=superuser_membership.tenant)
        target = MembershipFactory(tenant=superuser_membership.tenant)
        TeamMembershipFactory(team=team, membership=target)
        response = superuser_client.post(
            self.url,
            {"team_id": str(team.pk), "membership_id": str(target.pk)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_admin_cannot_add_member(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Regular members cannot add team memberships."""
        team = TeamFactory(tenant=membership.tenant)
        response = auth_client.post(
            self.url,
            {"team_id": str(team.pk), "membership_id": str(membership.pk)},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_add_member_from_other_tenant(
        self,
        superuser_client: APIClient,
        superuser_membership: TenantMembership,
    ) -> None:
        """Cannot add a membership from a different tenant."""
        team = TeamFactory(tenant=superuser_membership.tenant)
        other_membership = MembershipFactory()  # Different tenant
        response = superuser_client.post(
            self.url,
            {"team_id": str(team.pk), "membership_id": str(other_membership.pk)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTeamMembershipDelete:
    """Tests for DELETE /api/teams/memberships/{id}/."""

    url = "/api/teams/memberships/"

    def test_remove_member_from_team(
        self,
        superuser_client: APIClient,
        superuser_membership: TenantMembership,
    ) -> None:
        """Admin can remove a member from a team (hard delete)."""
        team = TeamFactory(tenant=superuser_membership.tenant)
        tm = TeamMembershipFactory(team=team, membership=superuser_membership)
        response = superuser_client.delete(f"{self.url}{tm.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TeamMembership.objects.filter(pk=tm.pk).exists()

    def test_non_admin_cannot_remove_member(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Regular members cannot remove team memberships."""
        team = TeamFactory(tenant=membership.tenant)
        tm = TeamMembershipFactory(team=team, membership=membership)
        response = auth_client.delete(f"{self.url}{tm.pk}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
