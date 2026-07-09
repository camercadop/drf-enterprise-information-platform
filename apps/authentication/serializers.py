from typing import Any

from django.contrib.auth.hashers import check_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from core.utils.security import validate_password_complexity

from .models import PASSWORD_HISTORY_LIMIT, UserPasswordHistory


class LoginSerializer(TokenObtainPairSerializer):  # type: ignore[type-arg]
    """Authenticates user and returns JWT token pair with basic user info."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.pk),
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }
        return data


class RefreshSerializer(TokenRefreshSerializer):  # type: ignore[type-arg]
    """Accepts a refresh token and returns a new access token."""


class LogoutSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Blacklists the provided refresh token to invalidate the session."""

    refresh = serializers.CharField()

    def validate_refresh(self, value: str) -> str:
        try:
            self._token = RefreshToken(value)  # type: ignore[arg-type]
        except Exception as e:
            raise serializers.ValidationError("Invalid or expired token.") from e
        return value

    def save(self, **kwargs: Any) -> None:
        self._token.blacklist()


class PasswordChangeSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Validates old password and enforces complexity on the new one."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirmation = serializers.CharField(write_only=True)

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["new_password"] != attrs["new_password_confirmation"]:
            raise serializers.ValidationError(
                {"new_password_confirmation": "Passwords do not match."}
            )
        result = validate_password_complexity(attrs["new_password"])
        if not result["is_valid"]:
            raise serializers.ValidationError({"new_password": result["errors"]})

        user = self.context["request"].user
        recent = UserPasswordHistory.objects.filter(user=user)[:PASSWORD_HISTORY_LIMIT]
        for entry in recent:
            if check_password(attrs["new_password"], entry.hashed_password):
                raise serializers.ValidationError(
                    {
                        "new_password": f"Cannot reuse any of your last {PASSWORD_HISTORY_LIMIT} passwords."
                    }
                )
        return attrs

    def save(self, **kwargs: Any) -> None:
        user = self.context["request"].user
        # Save current password to history before changing
        UserPasswordHistory.objects.create(user=user, hashed_password=user.password)
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
