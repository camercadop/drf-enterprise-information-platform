"""Tests for core.filters.base."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.tenants.models import Tenant
from tests.factories.dms_document_types import DocumentTypeFactory
from tests.factories.tenants import TenantFactory
from tests.factories.users import UserFactory


def _make_view(filterset_fields: list | None = None, filterset_class: type | None = None) -> MagicMock:
    view = MagicMock()
    view.filterset_fields = filterset_fields
    view.filterset_class = filterset_class
    return view


def _make_request(user: object = None, params: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.user = user or MagicMock(is_authenticated=False)
    request.query_params = params or {}
    return request


@pytest.mark.django_db
class TestSmartFilterBackend:
    def test_returns_none_when_no_filterset_fields(self) -> None:
        from core.filters.base import SmartFilterBackend

        backend = SmartFilterBackend()
        view = _make_view(filterset_fields=None)
        result = backend.get_filterset_class(view, Tenant.objects.all())
        assert result is None

    def test_returns_none_when_queryset_is_none(self) -> None:
        from core.filters.base import SmartFilterBackend

        backend = SmartFilterBackend()
        view = _make_view(filterset_fields=["name"])
        result = backend.get_filterset_class(view, None)
        assert result is None

    def test_delegates_to_super_when_filterset_class_set(self) -> None:
        from core.filters.base import SmartFilterBackend

        backend = SmartFilterBackend()
        custom_class = MagicMock()
        view = _make_view(filterset_class=custom_class)

        with patch.object(SmartFilterBackend.__bases__[0], "get_filterset_class", return_value=custom_class):
            result = backend.get_filterset_class(view, Tenant.objects.all())

        assert result == custom_class

    def test_generates_filterset_class_for_declared_fields(self) -> None:
        from core.filters.base import SmartFilterBackend

        backend = SmartFilterBackend()
        view = _make_view(filterset_fields=["name"])

        with override_settings(VIEWSET_FILTER_MULTI_VALUE_SEPARATOR=","):
            filterset_class = backend.get_filterset_class(view, Tenant.objects.all())

        assert filterset_class is not None
        assert "name" in filterset_class.base_filters
        assert "name__icontains" in filterset_class.base_filters
        assert "name__in" in filterset_class.base_filters

    def test_in_filter_splits_by_separator(self) -> None:
        from core.filters.base import SmartFilterBackend

        backend = SmartFilterBackend()
        view = _make_view(filterset_fields=["name"])

        with override_settings(VIEWSET_FILTER_MULTI_VALUE_SEPARATOR=","):
            filterset_class = backend.get_filterset_class(view, Tenant.objects.all())

        in_filter = filterset_class.base_filters["name__in"]
        qs = Tenant.objects.all()
        result = in_filter.filter(qs, "a,b,c")
        assert result is not None


@pytest.mark.django_db
class TestSoftDeleteFilterBackend:
    def test_excludes_soft_deleted_by_default(self) -> None:
        from core.filters.base import SoftDeleteFilterBackend

        tenant = TenantFactory()
        tenant.delete()

        backend = SoftDeleteFilterBackend()
        request = _make_request()
        qs = Tenant.objects.all()

        result = backend.filter_queryset(request, qs, MagicMock())

        assert not result.filter(pk=tenant.pk).exists()

    def test_superuser_can_include_deleted(self) -> None:
        from apps.dms_document_types.models import DocumentType
        from core.filters.base import SoftDeleteFilterBackend

        doc_type = DocumentTypeFactory()
        doc_type_pk = doc_type.pk
        doc_type.delete()

        user = UserFactory(is_superuser=True)
        backend = SoftDeleteFilterBackend()
        request = _make_request(user=user, params={"include_deleted": "true"})
        qs = DocumentType.objects.filter(pk=doc_type_pk)

        result = backend.filter_queryset(request, qs, MagicMock())

        assert result.filter(pk=doc_type_pk).exists()

    def test_non_admin_cannot_include_deleted(self) -> None:
        from apps.dms_document_types.models import DocumentType
        from core.filters.base import SoftDeleteFilterBackend
        from unittest.mock import PropertyMock

        doc_type = DocumentTypeFactory()
        doc_type_pk = doc_type.pk
        doc_type.delete()

        user = UserFactory(is_superuser=False)
        backend = SoftDeleteFilterBackend()
        request = _make_request(user=user, params={"include_deleted": "true"})

        with patch.object(
            type(user),
            "memberships",
            new_callable=PropertyMock,
            return_value=MagicMock(**{"filter.return_value.exists.return_value": False}),
        ):
            qs = DocumentType.objects.filter(pk=doc_type_pk)
            result = backend.filter_queryset(request, qs, MagicMock())

        assert not result.filter(pk=doc_type_pk).exists()

    def test_passes_through_queryset_without_deleted_at_field(self) -> None:
        from core.filters.base import SoftDeleteFilterBackend
        from django.contrib.auth import get_user_model

        User = get_user_model()
        backend = SoftDeleteFilterBackend()
        request = _make_request()
        qs = User.objects.all()

        result = backend.filter_queryset(request, qs, MagicMock())

        assert result is qs
