"""Tests for Team CRUD endpoints."""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_teams.models import Team
from apps.iam_users.models import TenantMembership
from tests.base import BaseCRUDAPITest
from tests.factories.teams import TeamFactory


class TestTeamViewSet(BaseCRUDAPITest):
    """Tests for /api/teams/ CRUD."""

    url = "/api/teams/"

    @pytest.fixture(autouse=True)
    def _setup_base(
        self, superuser_client: APIClient, superuser: Any, superuser_membership: TenantMembership
    ) -> None:
        self.client = superuser_client
        self.user = superuser
        self.membership = superuser_membership

    def create_instance(self) -> Team:
        return TeamFactory(tenant=self.membership.tenant)

    def valid_payloads(self) -> list[dict[str, Any]]:
        return [
            {"name": "Engineering", "description": "Backend team"},
            {"name": "Design", "description": ""},
        ]

    def invalid_payloads(self) -> list[tuple[dict[str, Any], list[str | dict[str, str]] | None]]:
        return [
            ({"name": ""}, None),
        ]


@pytest.mark.django_db
class TestTeamViewSetPermissions:
    """Tests for Team write permission enforcement."""

    def test_non_admin_cannot_create_team(
        self, auth_client: APIClient
    ) -> None:
        """Regular members cannot create teams."""
        response = auth_client.post(
            "/api/teams/", {"name": "New Team"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_authenticated_user_can_list_teams(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Authenticated users can list teams in their tenant."""
        TeamFactory(tenant=membership.tenant)
        response = auth_client.get("/api/teams/")
        assert response.status_code == status.HTTP_200_OK
