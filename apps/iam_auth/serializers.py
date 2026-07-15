from typing import Any

from django.contrib.auth.hashers import check_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.iam_users.models import TenantMembership
from core.utils.security import validate_password_complexity

from .models import PASSWORD_HISTORY_LIMIT, UserPasswordHistory


class LoginSerializer(TokenObtainPairSerializer):  # type: ignore[type-arg]
    """Authenticates user and returns JWT token pair with tenant context."""

    tenant_id = serializers.UUIDField(required=False)

    @classmethod
    def get_token(cls, user: Any) -> RefreshToken:
        return super().get_token(user)  # type: ignore[return-value]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        tenant_id = attrs.pop("tenant_id", None)
        data: dict[str, Any] = super().validate(attrs)

        membership = self._resolve_tenant_membership(tenant_id)

        # Generate tokens with tenant_id claim
        resolved_tenant_id = str(membership.tenant_id)
        refresh = self.get_token(self.user)
        refresh["tenant_id"] = resolved_tenant_id
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        data["user"] = {
            "id": str(self.user.pk),
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "tenant_id": resolved_tenant_id,
        }
        return data

    def _resolve_tenant_membership(self, tenant_id: Any) -> TenantMembership:
        """Resolve which tenant the user is logging into."""
        memberships = TenantMembership.objects.filter(
            user=self.user, is_active=True
        ).select_related("tenant")

        if not memberships.exists():
            raise serializers.ValidationError(
                {"detail": "User has no active tenant memberships."},
                code="no_tenant_membership",
            )

        if tenant_id:
            membership = memberships.filter(tenant_id=tenant_id).first()
            if not membership:
                raise serializers.ValidationError(
                    {"tenant_id": "User does not belong to this tenant."},
                    code="invalid_tenant",
                )
            return membership  # type: ignore[no-any-return]

        if memberships.count() == 1:
            return memberships.first()  # type: ignore[no-any-return]

        # User has multiple tenants and didn't specify which one
        available = [
            {"id": str(m.tenant_id), "name": m.tenant.name}
            for m in memberships
        ]
        raise serializers.ValidationError(
            {
                "tenant_id": "This field is required when the user belongs to multiple tenants.",
                "available_tenants": available,
            },
            code="tenant_required",
        )


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

        # Load password policy from tenant settings (stored as JSON text)
        import json

        from apps.tenants.utils import get_tenant_id, get_tenant_setting

        config: dict[str, Any] | None = None
        tenant_id = get_tenant_id(self.context["request"])
        if tenant_id:
            raw = get_tenant_setting(tenant_id, "password_policy")
            if raw:
                config = json.loads(raw)

        result = validate_password_complexity(attrs["new_password"], config)
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


class PasswordChangeResponseSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Response schema for password change (new access token)."""

    access = serializers.CharField()
