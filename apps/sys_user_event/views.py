"""Views for sys_user_event read-only endpoints."""

import logging
from typing import Any

from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated

from apps.sys_user_event.models import AuthAttemptLog, UserEvent
from apps.tenants.permissions import IsTenantAdmin
from core.base.views import BaseGenericViewSet
from core.permissions.base import IsSuperUser

from .serializers import AuthAttemptLogSerializer, UserEventSerializer

logger = logging.getLogger(__name__)


class UserEventViewSet(mixins.ListModelMixin, BaseGenericViewSet):
    """Read-only list of user behavioral events.

    Superusers see all records. Tenant admins see only records scoped
    to their tenant. Requires authentication.
    """

    serializer_class = UserEventSerializer
    queryset = UserEvent.objects.all()
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    filterset_fields = [
        "category",
        "event",
        "actor",
        "tenant",
        "created_at",
    ]

    def get_permissions(self) -> list[Any]:
        """Allow superusers and tenant admins."""
        if self.request.user and self.request.user.is_superuser:  # type: ignore[union-attr]
            return [IsSuperUser()]
        return [IsAuthenticated(), IsTenantAdmin()]


class AuthAttemptLogViewSet(mixins.ListModelMixin, BaseGenericViewSet):
    """Read-only list of authentication attempts.

    Superusers see all records. Tenant admins see only records scoped
    to their tenant. Requires authentication.
    """

    serializer_class = AuthAttemptLogSerializer
    queryset = AuthAttemptLog.objects.all()
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    filterset_fields = [
        "email",
        "ip_address",
        "success",
        "tenant_id",
        "created_at",
    ]

    def get_permissions(self) -> list[Any]:
        """Allow superusers and tenant admins."""
        if self.request.user and self.request.user.is_superuser:  # type: ignore[union-attr]
            return [IsSuperUser()]
        return [IsAuthenticated(), IsTenantAdmin()]
