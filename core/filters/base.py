"""
Base filters for the enterprise platform.
"""

from typing import Any

import django_filters as filters


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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Add common filters to all filter sets
        self.filters["id"] = filters.NumberFilter()
        self.filters["created_at"] = filters.DateTimeFilter()
        self.filters["updated_at"] = filters.DateTimeFilter()

    def get_filters(self) -> dict[str, Any]:
        """
        Get all filters including common ones.
        """
        filters_dict: dict[str, Any] = super().get_filters()
        # Add common filters
        filters_dict.update(
            {
                "id": filters.NumberFilter(),
                "created_at": filters.DateTimeFilter(),
                "updated_at": filters.DateTimeFilter(),
            }
        )
        return filters_dict


class SoftDeleteFilter(filters.FilterSet):
    """
    Filter for soft-deleted objects.
    """

    include_deleted = filters.BooleanFilter(
        field_name="deleted_at",
        label="Include deleted objects",
        widget=filters.BooleanWidget,
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
