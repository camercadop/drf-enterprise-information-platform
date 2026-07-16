"""Views for teams and team membership management."""

from typing import Any

from rest_framework import mixins, status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.tenants.utils import get_tenant_id
from core.base.views import BaseGenericViewSet, BaseViewSet
from core.exceptions.api import PermissionDeniedError
from core.permissions.base import IsSuperUser

from .models import Team, TeamMembership
from .serializers import (
    TeamListSerializer,
    TeamMembershipCreateSerializer,
    TeamMembershipSerializer,
    TeamSerializer,
)


class TeamViewSet(BaseViewSet):
    """CRUD for teams within a tenant."""

    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    serializer_classes = {
        "list": TeamListSerializer,
    }
    write_permission_classes = [IsSuperUser]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class TeamMembershipViewSet(
    BaseGenericViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
):
    """Manage team memberships (add/remove members from teams)."""

    queryset = TeamMembership.objects.select_related(
        "team", "membership__user"
    )
    serializer_class = TeamMembershipSerializer
    serializer_classes = {
        "create": TeamMembershipCreateSerializer,
    }
    write_permission_classes = [IsSuperUser]
    search_fields = ["membership__user__email", "team__name"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_serializer_context(self) -> dict[str, Any]:
        """Inject tenant_id into serializer context for create actions."""
        context: dict[str, Any] = super().get_serializer_context()
        if self.action == "create":
            tenant_id = get_tenant_id(self.request)
            if not tenant_id:
                if getattr(self, "swagger_fake_view", False):
                    return context
                raise PermissionDeniedError("No tenant context in token.")
            context["tenant_id"] = tenant_id
        return context

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Hard-delete a team membership (remove member from team)."""
        instance = self.get_object()
        instance.hard_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
