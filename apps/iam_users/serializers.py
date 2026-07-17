"""Serializers for the iam_users app."""

from typing import Any

from rest_framework import serializers

from .models import User, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Serializer for the UserProfile model."""

    class Meta:
        model = UserProfile
        fields = ["personal_info"]


class UserListSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Lightweight serializer for listing users."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_active"]


class UserDetailSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Serializer for retrieving a user with profile data."""

    personal_info = serializers.JSONField(
        source="profile.personal_info", read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "personal_info",
            "created_at",
            "updated_at",
        ]


class UserMeUpdateSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Serializer for updating the authenticated user's own profile.

    Email is intentionally excluded — it is the login credential and requires
    a dedicated verified-change flow. Use first_name, last_name, and
    personal_info for self-service updates.
    """

    personal_info = serializers.JSONField(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "personal_info"]

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        """Update User fields and delegate personal_info to UserProfile."""
        personal_info = validated_data.pop("personal_info", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(
            update_fields=list(validated_data.keys()) or ["first_name", "last_name"]
        )

        if personal_info is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            profile.personal_info = personal_info
            profile.save(update_fields=["personal_info"])

        return instance
