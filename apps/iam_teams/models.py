"""Tenant-scoped teams and team membership."""

from django.db import models

from apps.tenants.models import TenantAwareModel


class Team(TenantAwareModel):
    """A group within a tenant for organizing members.

    Teams allow tenants to subdivide their membership into logical groups
    (departments, projects, squads). A tenant member can belong to multiple teams.
    """

    name = models.CharField(max_length=255)
    # Display name of the team

    description = models.TextField(blank=True)
    # Optional description of the team's purpose

    is_active = models.BooleanField(default=True)
    # Whether the team is currently active

    class Meta:
        db_table = "iam_teams"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"], name="unique_team_per_tenant"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant})"


class TeamMembership(TenantAwareModel):
    """Links a tenant member to a team.

    Enforces that only users with an active tenant membership can be
    assigned to teams within that tenant. Uses FK to TenantMembership
    for referential integrity.
    """

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    # The team this membership belongs to

    membership = models.ForeignKey(
        "iam_users.TenantMembership",
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    # The tenant membership (user-tenant link) being added to the team

    class Meta:
        db_table = "iam_teams_memberships"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "membership"],
                name="unique_member_per_team",
            )
        ]

    def __str__(self) -> str:
        return f"{self.membership.user.email} @ {self.team.name}"
