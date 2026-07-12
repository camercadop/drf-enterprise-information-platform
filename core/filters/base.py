"""
Base filters for the enterprise platform.
"""

from typing import Any

import django_filters as filters
from django.db.models import QuerySet
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request


class SoftDeleteFilterBackend(BaseFilterBackend):
    """Excludes soft-deleted objects unless ?include_deleted=true is passed and user is superuser or tenant admin."""

    def filter_queryset(
        self, request: Request, queryset: QuerySet[Any], view: Any
    ) -> QuerySet[Any]:
        # Check if the user is allowed to see soft-deleted objects
        include_deleted_allowed = False
        if request.user and request.user.is_authenticated:
            # Superusers are allowed
            if request.user.is_superuser:
                include_deleted_allowed = True
            else:
                # Check if the user has any active tenant membership with is_admin=True
                # The related name for the user in TenantMembership is 'memberships'
                if hasattr(request.user, "memberships"):
                    include_deleted_allowed = request.user.memberships.filter(
                        is_active=True, is_admin=True
                    ).exists()

        # If the user is allowed and the parameter is set, then include deleted objects
        if include_deleted_allowed and request.query_params.get(
            "include_deleted", ""
        ).lower() in ("true", "1"):
            return queryset
        # Otherwise, filter out soft-deleted objects if the model has the field
        if hasattr(queryset.model, "deleted_at"):
            return queryset.filter(deleted_at__isnull=True)
        return queryset


class BaseFilterSet(filters.FilterSet):
    """
    Base FilterSet with common functionality.
    """

    # Common filter fields
    id = filters.NumberFilter()
    created_at = filters.DateTimeFilter()
    updated_at = filters.DateTimeFilter()

    class Meta:
        abstract = True


class SoftDeleteFilter(filters.FilterSet):
    """
    Filter for soft-deleted objects.
    """

    include_deleted = filters.BooleanFilter(
        field_name="deleted_at",
        label="Include deleted objects",
    )

    class Meta:
        abstract = True

    def filter_queryset(self, queryset: Any) -> Any:  # type: ignore[override]
        """
        Apply soft delete filtering.
        """
        if not self.data.get("include_deleted", False):
            if hasattr(queryset.model, "get_active"):
                queryset = queryset.model.get_active()
        return queryset
