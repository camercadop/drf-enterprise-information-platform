"""Views for the iam_users app."""

import logging
from typing import Any

from django.db.models import QuerySet
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.tenants.utils import get_tenant_id
from core.base.views import BaseGenericViewSet

from .models import User
from .serializers import (
    UserDetailSerializer,
    UserListSerializer,
    UserMeUpdateSerializer,
)

logger = logging.getLogger(__name__)


class UserViewSet(
    BaseGenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    """List and retrieve users, with a self-service /me endpoint.

    Superusers see all users. Authenticated non-superusers see only users
    who share at least one active tenant membership with them.
    """

    serializer_class = UserDetailSerializer
    serializer_classes = {
        "list": UserListSerializer,
        "me": UserDetailSerializer,
        "me_update": UserMeUpdateSerializer,
    }
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "created_at"]
    ordering = ["email"]

    def get_queryset(self) -> QuerySet[User]:
        """Return all users for superusers, or tenant-scoped users otherwise."""
        qs = User.objects.select_related("profile")
        if self.request.user.is_superuser:  # type: ignore[union-attr]
            return qs
        tenant_id = get_tenant_id(self.request)
        if not tenant_id:
            return qs.none()
        return qs.filter(
            memberships__tenant_id=tenant_id,
            memberships__is_active=True,
        ).distinct()

    def get_serializer_class(self) -> Any:
        """Dispatch to me_update serializer for PATCH /me/."""
        if self.action == "me" and self.request.method == "PATCH":
            return self.serializer_classes["me_update"]
        return self.serializer_classes.get(self.action, self.serializer_class)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request: Request) -> Response:
        """Retrieve or partially update the authenticated user's own profile.

        GET returns the full user detail including personal_info.
        PATCH allows updating first_name, last_name, and personal_info.
        Email is read-only and cannot be changed via this endpoint.
        """
        user: User = request.user  # type: ignore[assignment]

        if request.method == "PATCH":
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            logger.info("User profile updated user_id=%s", user.pk)
            return Response(
                UserDetailSerializer(user, context=self.get_serializer_context()).data
            )

        serializer = self.get_serializer(user)
        return Response(serializer.data)
