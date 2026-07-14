"""Tests for core.base.views.BaseViewSet."""

from typing import Any
from unittest.mock import MagicMock

from rest_framework.permissions import IsAuthenticated

from core.base.views import BaseViewSet
from core.permissions.base import IsSuperUser


class TestGetWriteActions:
    def test_returns_standard_write_actions(self) -> None:
        actions = BaseViewSet.get_write_actions()
        assert "create" in actions
        assert "update" in actions
        assert "partial_update" in actions
        assert "destroy" in actions

    def test_does_not_include_read_actions(self) -> None:
        actions = BaseViewSet.get_write_actions()
        assert "list" not in actions
        assert "retrieve" not in actions


class TestGetPermissions:
    def _make_viewset(self, action: str, write_perms: list[Any] | None = None) -> BaseViewSet:
        viewset = BaseViewSet()
        viewset.action = action
        viewset.write_permission_classes = write_perms
        return viewset

    def test_write_action_with_write_permissions(self) -> None:
        viewset = self._make_viewset("create", [IsSuperUser])
        perms = viewset.get_permissions()
        perm_classes = [type(p) for p in perms]
        assert IsAuthenticated in perm_classes
        assert IsSuperUser in perm_classes

    def test_read_action_uses_default_permissions(self) -> None:
        viewset = self._make_viewset("list", [IsSuperUser])
        perms = viewset.get_permissions()
        perm_classes = [type(p) for p in perms]
        assert IsAuthenticated in perm_classes
        assert IsSuperUser not in perm_classes

    def test_no_write_permissions_uses_default(self) -> None:
        viewset = self._make_viewset("create", None)
        perms = viewset.get_permissions()
        perm_classes = [type(p) for p in perms]
        assert IsAuthenticated in perm_classes


class TestGetSerializerClass:
    def test_returns_action_specific_serializer(self) -> None:
        viewset = BaseViewSet()
        viewset.action = "list"
        mock_serializer = MagicMock()
        viewset.serializer_classes = {"list": mock_serializer}
        viewset.serializer_class = MagicMock()
        assert viewset.get_serializer_class() == mock_serializer

    def test_falls_back_to_default(self) -> None:
        viewset = BaseViewSet()
        viewset.action = "retrieve"
        viewset.serializer_classes = {}
        default = MagicMock()
        viewset.serializer_class = default
        assert viewset.get_serializer_class() == default


class TestCleanData:
    def test_clean_create_data_passthrough(self) -> None:
        viewset = BaseViewSet()
        data = {"name": "test", "code": "t1"}
        assert viewset.clean_create_data(data) == data

    def test_clean_update_data_passthrough(self) -> None:
        viewset = BaseViewSet()
        data = {"name": "updated"}
        assert viewset.clean_update_data(data) == data


class TestLifecycleHooks:
    def test_perform_create_calls_hooks(self) -> None:
        viewset = BaseViewSet()
        serializer = MagicMock()
        instance = MagicMock()
        serializer.save.return_value = instance

        called: list[str] = []
        viewset.pre_create = lambda s: called.append("pre")  # type: ignore[assignment]
        viewset.post_create = lambda i: called.append("post")  # type: ignore[assignment]

        viewset.perform_create(serializer)

        serializer.save.assert_called_once()
        assert called == ["pre", "post"]

    def test_perform_update_calls_hooks(self) -> None:
        viewset = BaseViewSet()
        serializer = MagicMock()
        instance = MagicMock()
        serializer.save.return_value = instance

        called: list[str] = []
        viewset.pre_update = lambda s: called.append("pre")  # type: ignore[assignment]
        viewset.post_update = lambda i: called.append("post")  # type: ignore[assignment]

        viewset.perform_update(serializer)

        serializer.save.assert_called_once()
        assert called == ["pre", "post"]

    def test_perform_destroy_calls_hooks(self) -> None:
        viewset = BaseViewSet()
        instance = MagicMock()

        called: list[str] = []
        viewset.pre_destroy = lambda i: called.append("pre")  # type: ignore[assignment]
        viewset.post_destroy = lambda i: called.append("post")  # type: ignore[assignment]

        viewset.perform_destroy(instance)

        instance.delete.assert_called_once()
        assert called == ["pre", "post"]
