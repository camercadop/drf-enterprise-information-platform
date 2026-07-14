from typing import Any

from django.db.models import QuerySet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.tenants.utils import get_tenant_id
from apps.users.models import TenantMembership
from core.base.views import BaseViewSet
from core.exceptions.api import ConflictError, PermissionDeniedError
from core.permissions.base import IsSuperUser, IsTenantAdmin

from .models import Team, Tenant
from .serializers import (
    MembershipCreateSerializer,
    MembershipListSerializer,
    TeamListSerializer,
    TeamSerializer,
    TenantListSerializer,
    TenantSerializer,
)


class TenantViewSet(BaseViewSet):
    """CRUD for tenants."""

    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    serializer_classes = {
        "list": TenantListSerializer,
    }
    write_permission_classes = [IsSuperUser]
    tenant_scoping = False
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self) -> QuerySet[Tenant]:
        qs = super().get_queryset()
        if self.request.user.is_superuser:  # type: ignore[union-attr]
            return qs
        return qs.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        )


class MembershipViewSet(BaseViewSet):
    """Manage tenant memberships (invite, remove, list)."""

    queryset = TenantMembership.objects.select_related("user", "role")
    serializer_class = MembershipListSerializer
    serializer_classes = {
        "create": MembershipCreateSerializer,
    }
    write_permission_classes = [IsTenantAdmin]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    ordering_fields = ["joined_at"]
    ordering = ["-joined_at"]

    def get_serializer_context(self) -> dict[str, Any]:
        context: dict[str, Any] = super().get_serializer_context()
        if self.action == "create":
            tenant_id = get_tenant_id(self.request)
            if not tenant_id:
                raise PermissionDeniedError("No tenant context in token.")
            context["tenant_id"] = tenant_id
        return context

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk: str | None = None) -> Response:
        """Deactivate a membership (soft remove).

        Validates that the membership is currently active before applying
        the transition. Returns 409 if already deactivated.
        """
        membership = self.get_object()
        if not membership.is_active:
            raise ConflictError("Membership is already deactivated.")
        membership.is_active = False
        membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk: str | None = None) -> Response:
        """Re-activate a previously deactivated membership.

        Validates that the membership is currently inactive before applying
        the transition. Returns 409 if already active.
        """
        membership = self.get_object()
        if membership.is_active:
            raise ConflictError("Membership is already active.")
        membership.is_active = True
        membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamViewSet(BaseViewSet):
    """CRUD for teams."""

    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    serializer_classes = {
        "list": TeamListSerializer,
    }
    write_permission_classes = [IsSuperUser]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    @property
    def tenant_scoping(self) -> bool:  # type: ignore[override]
        """Superusers see all teams across tenants."""
        if self.request.user.is_superuser:  # type: ignore[union-attr]
            return False
        return True
