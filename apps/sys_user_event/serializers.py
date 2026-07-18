"""Serializers for sys_user_event read-only endpoints."""

from rest_framework import serializers

from apps.sys_user_event.models import AuthAttemptLog, UserEvent


class UserEventSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Read-only serializer for UserEvent list endpoint."""

    class Meta:
        model = UserEvent
        fields = [
            "id",
            "actor",
            "user_email",
            "category",
            "event",
            "tenant_id",
            "metadata",
            "created_at",
        ]


class AuthAttemptLogSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Read-only serializer for AuthAttemptLog list endpoint."""

    class Meta:
        model = AuthAttemptLog
        fields = [
            "id",
            "email",
            "ip_address",
            "success",
            "failure_reason",
            "tenant_id",
            "created_at",
        ]
