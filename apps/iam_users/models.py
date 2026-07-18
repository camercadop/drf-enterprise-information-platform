"""Platform-level user identity, profiles, and tenant membership."""

from __future__ import annotations

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from apps.tenants.managers import TenantManager


class UserManager(BaseUserManager["User"]):
    def create_user(
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> User:
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user  # type: ignore[no-any-return]

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> User:
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the user

    email = models.EmailField(unique=True)
    # Primary login credential and unique identifier

    first_name = models.CharField(max_length=150, blank=True)
    # User's given name

    last_name = models.CharField(max_length=150, blank=True)
    # User's family name

    is_active = models.BooleanField(default=True)
    # Whether the user can log in

    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the user was created

    updated_at = models.DateTimeField(auto_now=True)
    # Timestamp when the user was last updated

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    fk_representation_fields = ["id", "email", "first_name", "last_name"]

    class Meta:
        db_table = "iam_users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return str(self.email)


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the profile

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    # Link back to the user

    personal_info = models.JSONField(default=dict, blank=True)
    # Flexible key-value store for personal details (phone, avatar, bio, etc.)

    class Meta:
        db_table = "iam_users_profiles"
        ordering = ["-user__created_at"]

    def __str__(self) -> str:
        return f"Profile({self.user.email})"


class TenantMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the membership

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    # The user who belongs to the tenant

    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="memberships"
    )
    # The tenant the user belongs to

    role = models.ForeignKey(
        "iam_roles.TenantRole", on_delete=models.PROTECT, related_name="memberships"
    )
    # The user's role within this tenant

    is_admin = models.BooleanField(default=False)
    # Whether the user has admin privileges in this tenant

    is_active = models.BooleanField(default=True)
    # Whether this membership is currently active

    joined_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the user joined the tenant

    objects = TenantManager()

    class Meta:
        db_table = "iam_users_memberships"
        ordering = ["-joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tenant"], name="unique_user_tenant"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.tenant}"
