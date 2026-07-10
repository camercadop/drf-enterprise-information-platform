from typing import Any

from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated

from core.base.views import BaseViewSet
from core.permissions.base import IsSuperUser

from .models import Tenant
from .serializers import TenantListSerializer, TenantSerializer


class TenantViewSet(BaseViewSet):
    """CRUD for tenants."""

    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    serializer_classes = {
        "list": TenantListSerializer,
    }
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self) -> list[Any]:
        if self.action in self.get_write_actions():
            return [IsAuthenticated(), IsSuperUser()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet[Tenant]:
        qs = super().get_queryset()
        if self.request.user.is_superuser:  # type: ignore[union-attr]
            return qs
        return qs.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        )
