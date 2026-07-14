"""Tests for ForeignKeyField.get_queryset and .fail methods."""

from unittest.mock import MagicMock

import pytest
from rest_framework.exceptions import ValidationError

from core.fields.related import ForeignKeyField


class TestForeignKeyFieldGetQueryset:
    def _make_field(self, **kwargs: object) -> ForeignKeyField:
        qs = MagicMock()
        qs.filter.return_value = qs
        field = ForeignKeyField(queryset=qs, **kwargs)
        field._context = {"tenant_id": "t1"}
        field.bind("role", None)
        return field

    @property
    def _default_context(self) -> dict[str, str]:
        return {"tenant_id": "t1"}

    def test_filters_deleted_at_by_default(self) -> None:
        field = self._make_field()
        field._context = self._default_context
        qs = field.get_queryset()
        calls = [str(c) for c in qs.filter.call_args_list]
        assert any("deleted_at__isnull" in c for c in calls)

    def test_skips_deleted_filter_when_disabled(self) -> None:
        qs = MagicMock()
        qs.filter.return_value = qs
        field = ForeignKeyField(queryset=qs, exclude_deleted=False, context_filters={})
        field._context = {}
        field.bind("role", None)
        result = field.get_queryset()
        # Should not have been called with deleted_at filter
        for call in qs.filter.call_args_list:
            assert "deleted_at__isnull" not in str(call.kwargs)

    def test_applies_base_filters(self) -> None:
        qs = MagicMock()
        qs.filter.return_value = qs
        field = ForeignKeyField(
            queryset=qs,
            base_filters={"is_active": True},
            context_filters={},
            exclude_deleted=False,
        )
        field._context = {}
        field.bind("role", None)
        field.get_queryset()
        qs.filter.assert_called_once_with(is_active=True)

    def test_applies_context_filters(self) -> None:
        qs = MagicMock()
        qs.filter.return_value = qs
        field = ForeignKeyField(
            queryset=qs,
            context_filters={"tenant_id": "tenant_id"},
            exclude_deleted=False,
        )
        field._context = {"tenant_id": "abc-123"}
        field.bind("role", None)
        field.get_queryset()
        qs.filter.assert_called_once_with(tenant_id="abc-123")


class TestForeignKeyFieldFail:
    def test_does_not_exist_raises_custom_message(self) -> None:
        qs = MagicMock()
        field = ForeignKeyField(queryset=qs, error_message="Role not found.")
        field.bind("role", None)
        with pytest.raises(ValidationError, match="Role not found."):
            field.fail("does_not_exist", pk_value="123")

    def test_other_keys_delegate_to_parent(self) -> None:
        qs = MagicMock()
        field = ForeignKeyField(queryset=qs)
        field.bind("role", None)
        with pytest.raises(Exception):
            field.fail("incorrect_type", data_type="list")
