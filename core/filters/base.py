"""
Base filters for the enterprise platform.
"""

from typing import Any

import django_filters as filters
from django.conf import settings
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request

SUPPORTED_LOOKUPS = {"exact", "gte", "lte", "gt", "lt", "icontains", "in", "isnull"}


def _is_fk_field(model: type[Any], field_name: str) -> bool:
    """Return True if field_name is a ForeignKey on the given model."""
    try:
        field = model._meta.get_field(field_name)  # type: ignore[attr-defined]
        return bool(field.many_to_one or field.one_to_one)  # type: ignore[union-attr]
    except Exception:
        return False


class SmartFilterBackend(DjangoFilterBackend):
    """DjangoFilterBackend subclass that auto-generates filters from filterset_fields.

    For each field declared in ``filterset_fields``, generates one filter per
    supported lookup. Callers use query params with suffixes (e.g.,
    ``?created_at__gte=...``) without needing to declare them explicitly.
    Fields are matched by exact lookup when no suffix is provided.

    Supported suffixes: exact, gte, lte, gt, lt, icontains, in, isnull.

    The ``in`` lookup splits values by a configurable separator. Configure via
    ``VIEWSET_FILTER_MULTI_VALUE_SEPARATOR`` in settings (default: ``,``).
    """

    def get_filterset_class(self, view: Any, queryset: QuerySet[Any] | None = None) -> type | None:  # type: ignore[override]
        """Build a FilterSet class dynamically from filterset_fields with all supported lookups.

        Falls back to the default DjangoFilterBackend behaviour when
        ``filterset_class`` is explicitly set on the view.
        """
        if getattr(view, "filterset_class", None):
            return super().get_filterset_class(view, queryset)  # type: ignore[return-value, no-any-return]

        filterset_fields: list[str] | None = getattr(view, "filterset_fields", None)
        if not filterset_fields or queryset is None:
            return None

        separator: str = getattr(settings, "VIEWSET_FILTER_MULTI_VALUE_SEPARATOR", ",")
        model = queryset.model
        filter_fields: dict[str, filters.Filter] = {}

        for field_name in filterset_fields:
            db_field = f"{field_name}_id" if _is_fk_field(model, field_name) else field_name
            for lookup in SUPPORTED_LOOKUPS:
                key = field_name if lookup == "exact" else f"{field_name}__{lookup}"

                if lookup == "in":
                    def _make_in_filter(fname: str, sep: str, label: str) -> filters.BaseInFilter:  # type: ignore[type-arg]
                        class _InFilter(filters.BaseInFilter):  # type: ignore[type-arg]
                            def filter(self, qs: QuerySet[Any], value: str) -> QuerySet[Any]:
                                if value:
                                    values = [v.strip() for v in value.split(sep)]
                                    return super().filter(qs, values)
                                return qs
                        return _InFilter(field_name=fname, lookup_expr="in", label=label)

                    filter_fields[key] = _make_in_filter(db_field, separator, key)
                else:
                    filter_fields[key] = filters.CharFilter(
                        field_name=db_field, lookup_expr=lookup, label=key
                    )

        meta_class = type("Meta", (), {"model": model, "fields": []})
        filterset_class: type = type(
            "AutoFilterSet",
            (filters.FilterSet,),
            {**filter_fields, "Meta": meta_class},
        )
        return filterset_class


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
