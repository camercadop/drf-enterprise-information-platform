"""
Base views for the enterprise platform.
"""

from typing import Any

from django.db.models import Model, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, viewsets
from rest_framework.filters import BaseFilterBackend
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request


class SoftDeleteFilterBackend(BaseFilterBackend):
    """
    Excludes soft-deleted objects unless ?include_deleted=true is passed.
    """

    def filter_queryset(
        self, request: Request, queryset: QuerySet[Any], view: Any
    ) -> QuerySet[Any]:
        if request.query_params.get("include_deleted", "").lower() == "true":
            return queryset
        if hasattr(queryset.model, "deleted_at"):
            return queryset.filter(deleted_at__isnull=True)
        return queryset


class BaseViewSet(viewsets.ModelViewSet):
    """
    Base viewset with common functionality for all models.

    Attributes:
        serializer_classes: Per-action serializer mapping. Falls back to serializer_class.
        querysets: Per-action queryset mapping. Falls back to queryset.
    """

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        SoftDeleteFilterBackend,
    ]
    search_fields: list[str] = []
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated]
    write_permission_classes: list[type[BasePermission]] | None = None

    serializer_classes: dict[str, type[serializers.Serializer]] = {}
    querysets: dict[str, QuerySet[Any]] = {}

    # --- Action classification ---

    @classmethod
    def get_write_actions(cls) -> list[str]:
        """Return actions that perform write operations."""
        return ["create", "update", "partial_update", "destroy"]

    # --- Permissions ---

    def get_permissions(self) -> list[BasePermission]:
        if self.write_permission_classes and self.action in self.get_write_actions():
            return [p() for p in [IsAuthenticated, *self.write_permission_classes]]
        return [p() for p in self.permission_classes]

    # --- Dispatch by action ---

    def get_serializer_class(self) -> type[serializers.Serializer]:
        cls: type[serializers.Serializer] = self.serializer_classes.get(
            self.action, super().get_serializer_class()
        )
        return cls

    def get_queryset(self) -> QuerySet[Any]:
        return self.querysets.get(self.action, super().get_queryset())

    def get_serializer(self, *args: Any, **kwargs: Any) -> serializers.Serializer:
        if "data" in kwargs:
            if self.action == "create":
                kwargs["data"] = self.clean_create_data(kwargs["data"])
            elif self.action in ("update", "partial_update"):
                kwargs["data"] = self.clean_update_data(kwargs["data"])
        return super().get_serializer(*args, **kwargs)

    # --- Data preparation ---

    def clean_create_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Prepare raw request data before serializer instantiation on create."""
        return data

    def clean_update_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Prepare raw request data before serializer instantiation on update."""
        return data

    # --- Create lifecycle ---

    def perform_create(self, serializer: serializers.Serializer) -> None:
        self.pre_create(serializer)
        instance = serializer.save()
        self.post_create(instance)

    def pre_create(self, serializer: serializers.Serializer) -> None:
        pass

    def post_create(self, instance: Model) -> None:
        pass

    # --- Update lifecycle ---

    def perform_update(self, serializer: serializers.Serializer) -> None:
        self.pre_update(serializer)
        instance = serializer.save()
        self.post_update(instance)

    def pre_update(self, serializer: serializers.Serializer) -> None:
        pass

    def post_update(self, instance: Model) -> None:
        pass

    # --- Destroy lifecycle ---

    def perform_destroy(self, instance: Model) -> None:
        self.pre_destroy(instance)
        instance.delete()
        self.post_destroy(instance)

    def pre_destroy(self, instance: Model) -> None:
        pass

    def post_destroy(self, instance: Model) -> None:
        pass
