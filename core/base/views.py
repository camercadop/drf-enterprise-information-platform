"""
Base views for the enterprise platform.
"""

from typing import Any

from django.conf import settings
from django.db.models import Model, QuerySet
from django.utils.module_loading import import_string
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated

from core.base.serializers import SerializerPlugin


class BaseGenericViewSet(viewsets.GenericViewSet):
    """Foundation viewset with all shared infrastructure.

    Provides per-action serializer/queryset dispatch, data cleaning hooks,
    pre_*/post_* lifecycle methods, permission dispatch, and global plugin
    dispatch for cross-cutting concerns (e.g., audit logging).

    Does not include any CRUD mixins — subclasses compose the actions they need.

    Attributes:
        serializer_classes: Per-action serializer mapping. Falls back to serializer_class.
        querysets: Per-action queryset mapping. Falls back to queryset.
    """

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
        self._run_plugins("on_post_destroy", instance)

    def pre_destroy(self, instance: Model) -> None:
        pass

    def post_destroy(self, instance: Model) -> None:
        pass

    # --- Plugin dispatch ---

    def _get_plugins(self) -> list[SerializerPlugin]:
        """Resolve global serializer plugins from settings.

        Returns:
            List of instantiated plugin objects.
        """
        global_paths: list[str] = getattr(settings, "SERIALIZER_PLUGINS", [])
        return [import_string(path)() for path in global_paths]

    def _run_plugins(self, hook: str, *args: Any) -> None:
        """Dispatch a named hook to all global serializer plugins.

        Passes the current action's serializer (for request context access)
        followed by any additional arguments. Skips dispatch if serializer
        context is unavailable (e.g., no request bound).

        Args:
            hook: The plugin method name to invoke.
            *args: Positional arguments forwarded to the hook after the serializer.
        """
        try:
            serializer = self.get_serializer()
        except AttributeError, AssertionError:
            return
        for plugin in self._get_plugins():
            if hasattr(plugin, hook):
                getattr(plugin, hook)(serializer, *args)


class BaseViewSet(  # type: ignore[misc]
    BaseGenericViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
):
    """Full CRUD viewset — default for most resources.

    Equivalent to ModelViewSet but built on BaseGenericViewSet infrastructure.
    Use this when the resource supports all CRUD operations.
    """


class BaseReadOnlyViewSet(
    BaseGenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    """Read-only viewset (list + retrieve).

    Use for resources that should never be created, updated, or deleted
    via the API (e.g., audit logs, system events).
    """
