"""Serializers for teams and team membership."""

from typing import Any

from rest_framework import serializers

from apps.iam_users.models import TenantMembership
from core.base.serializers import DefaultModelSerializer
from core.fields import ForeignKeyField
from core.validators import UniqueTogetherContextValidator

from .models import Team, TeamMembership


class TeamSerializer(DefaultModelSerializer):
    """Serializer for Team create and update operations."""

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = [
            UniqueTogetherContextValidator(
                fields={"name": "name"},
                message="A team with this name already exists in this tenant.",
            ),
        ]


class TeamListSerializer(DefaultModelSerializer):
    """Lightweight serializer for listing teams."""

    class Meta:
        model = Team
        fields = ["id", "name", "description", "is_active"]


class TeamMembershipSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Serializer for listing team memberships."""

    team = ForeignKeyField(read_only=True)
    membership = ForeignKeyField(read_only=True, representation_fields=["id", "user"])

    class Meta:
        model = TeamMembership
        fields = [
            "id",
            "team",
            "membership",
            "created_at",
        ]


class TeamMembershipCreateSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Serializer for adding a member to a team."""

    team_id = ForeignKeyField(
        queryset=Team.objects.all(),
        context_filters={"tenant_id": "tenant_id"},
        error_message="Team not found in this tenant.",
    )
    membership_id = ForeignKeyField(
        queryset=TenantMembership.objects.all(),
        base_filters={"is_active": True},
        context_filters={"tenant_id": "tenant_id"},
        exclude_deleted=False,
        error_message="Membership not found or inactive in this tenant.",
    )

    class Meta:
        model = TeamMembership
        validators = [
            UniqueTogetherContextValidator(
                fields={"team_id": "team_id", "membership_id": "membership_id"},
                message="This member is already in the team.",
            ),
        ]

    def create(self, validated_data: dict[str, Any]) -> TeamMembership:
        """Create a TeamMembership linking the member to the team."""
        tenant_id = self.context["tenant_id"]
        instance: TeamMembership = TeamMembership.objects.create(
            team_id=validated_data["team_id"].pk,
            membership_id=validated_data["membership_id"].pk,
            tenant_id=tenant_id,
        )
        return instance
