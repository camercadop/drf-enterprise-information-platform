"""Views for the iam_roles app."""

from apps.iam_roles.models import TenantRole
from core.base.views import BaseViewSet
from core.permissions.base import IsTenantAdmin

from .serializers import TenantRoleListSerializer, TenantRoleSerializer


class TenantRoleViewSet(BaseViewSet):
    """CRUD for tenant roles."""

    queryset = TenantRole.objects.all()
    serializer_class = TenantRoleSerializer
    serializer_classes = {
        "list": TenantRoleListSerializer,
    }
    write_permission_classes = [IsTenantAdmin]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
