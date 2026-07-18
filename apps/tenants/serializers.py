from typing import Any

from rest_framework import serializers

from apps.iam_roles.models import TenantRole
from apps.iam_users.models import TenantMembership, User
from core.fields import ForeignKeyField
from core.validators import UniqueTogetherContextValidator

from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Serializer for Tenant create and update operations."""

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "code",
            "is_active",
            "details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TenantListSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Lightweight serializer for listing tenants."""

    class Meta:
        model = Tenant
        fields = ["id", "name", "code", "is_active"]



class MembershipListSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Serializer for listing tenant memberships."""

    user = ForeignKeyField(read_only=True)
    role = ForeignKeyField(read_only=True)

    class Meta:
        model = TenantMembership
        fields = [
            "id",
            "user",
            "role",
            "is_admin",
            "is_active",
            "joined_at",
        ]


class MembershipCreateSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Serializer for inviting a user to a tenant."""

    user_id = ForeignKeyField(
        queryset=User.objects.all(),
        base_filters={"is_active": True},
        context_filters={},
        exclude_deleted=False,
        error_message="User not found or inactive.",
    )
    role_id = ForeignKeyField(
        queryset=TenantRole.objects.all(),
        error_message="Role not found in this tenant.",
    )
    is_admin = serializers.BooleanField(default=False)

    class Meta:
        model = TenantMembership
        validators = [
            UniqueTogetherContextValidator(
                fields={"user_id": "user_id"},
                message="User is already a member of this tenant.",
            ),
        ]

    def create(self, validated_data: dict[str, Any]) -> TenantMembership:
        tenant_id = self.context["tenant_id"]
        membership: TenantMembership = TenantMembership.objects.create(
            user_id=validated_data["user_id"].pk,
            tenant_id=tenant_id,
            role_id=validated_data["role_id"].pk,
            is_admin=validated_data["is_admin"],
        )
        return membership
