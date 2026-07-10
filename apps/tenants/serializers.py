from rest_framework import serializers

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
