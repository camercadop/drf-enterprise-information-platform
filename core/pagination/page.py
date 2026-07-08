"""
Custom pagination classes for the enterprise platform.
"""

from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    """
    Custom pagination class with enterprise features.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data: list[Any]) -> Response:
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "page_size": self.page_size,
                "current_page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "has_next": self.page.has_next(),
                "has_previous": self.page.has_previous(),
                "results": data,
            }
        )

    def get_page_size(self, request: Request) -> int:
        """
        Override to handle page size validation.
        """
        if self.page_size_query_param:
            try:
                page_size = int(request.query_params.get(self.page_size_query_param))  # type: ignore[arg-type]
                if page_size > self.max_page_size:
                    page_size = self.max_page_size
                return page_size
            except (ValueError, TypeError):
                pass
        return self.page_size


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination class for large datasets with optimized performance.
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000

    def get_paginated_response(self, data: list[Any]) -> Response:
        """
        Return a paginated response optimized for large datasets.
        """
        response = super().get_paginated_response(data)
        response.data.update(
            {
                "optimized": True,
                "cache_ttl": 300,  # 5 minutes
            }
        )
        return response

    def paginate_queryset(self, queryset: Any, request: Request, view: Any = None) -> list[Any] | None:
        """
        Optimize pagination for large datasets.
        """
        # Use select_related and prefetch_related for better performance
        if hasattr(queryset.model, "select_related"):
            queryset = queryset.select_related()
        if hasattr(queryset.model, "prefetch_related"):
            queryset = queryset.prefetch_related()

        return super().paginate_queryset(queryset, request, view)  # type: ignore[no-any-return]


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class for most use cases.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data: list[Any]) -> Response:
        """
        Return a standard paginated response.
        """
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


class OptimizedPagination(PageNumberPagination):
    """
    Highly optimized pagination for maximum performance.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500

    def paginate_queryset(self, queryset: Any, request: Request, view: Any = None) -> list[Any] | None:
        """
        Optimized pagination with minimal overhead.
        """
        # Use only essential optimizations
        if hasattr(queryset.model, "select_related"):
            queryset = queryset.select_related()

        return super().paginate_queryset(queryset, request, view)  # type: ignore[no-any-return]

    def get_paginated_response(self, data: list[Any]) -> Response:
        """
        Return a lightweight paginated response.
        """
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
