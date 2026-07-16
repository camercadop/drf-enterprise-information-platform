"""Tests for sys_audit.plugins.AuditSerializerPlugin."""

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.sys_audit.models import AuditLog
from apps.sys_audit.plugins import AuditSerializerPlugin
from tests.factories.users import UserFactory


@pytest.mark.django_db
class TestAuditSerializerPluginOnPostCreate:
    def test_records_create_action(self) -> None:
        user = UserFactory()
        plugin = AuditSerializerPlugin()
        serializer = self._make_serializer(user)
        instance = self._make_instance()

        plugin.on_post_create(serializer, instance)

        entry = AuditLog.objects.get(target_id=instance.pk)
        assert entry.action == "create"
        assert entry.actor == user

    def test_stores_full_payload_as_changes(self) -> None:
        user = UserFactory()
        plugin = AuditSerializerPlugin()
        representation = {"id": "abc", "name": "Test"}
        serializer = self._make_serializer(user, representation=representation)
        instance = self._make_instance()

        plugin.on_post_create(serializer, instance)

        entry = AuditLog.objects.get(target_id=instance.pk)
        assert entry.changes == representation

    def test_skips_when_no_actor(self) -> None:
        plugin = AuditSerializerPlugin()
        serializer = self._make_serializer(actor=None)
        instance = self._make_instance()

        plugin.on_post_create(serializer, instance)

        assert not AuditLog.objects.exists()

    def _make_serializer(
        self, actor: Any = None, representation: dict[str, Any] | None = None
    ) -> MagicMock:
        serializer = MagicMock()
        request = MagicMock()
        request.user = actor
        request.auth = {"tenant_id": str(uuid.uuid4())} if actor else None
        serializer.context = {"request": request}
        serializer.Meta.model._meta.label_lower = "tenants.team"
        serializer.to_representation.return_value = representation or {}
        return serializer

    def _make_instance(self) -> MagicMock:
        instance = MagicMock()
        instance.pk = uuid.uuid4()
        return instance


@pytest.mark.django_db
class TestAuditSerializerPluginOnPostUpdate:
    def test_records_update_action(self) -> None:
        user = UserFactory()
        plugin = AuditSerializerPlugin()
        serializer = self._make_serializer(user, validated_data={"name": "New"})
        instance = self._make_instance(name="Old")

        plugin.on_post_update(serializer, instance)

        entry = AuditLog.objects.get(target_id=instance.pk)
        assert entry.action == "update"

    def test_stores_diff_as_changes(self) -> None:
        user = UserFactory()
        plugin = AuditSerializerPlugin()
        serializer = self._make_serializer(user, validated_data={"name": "New"})
        instance = self._make_instance(name="Old")

        plugin.on_post_update(serializer, instance)

        entry = AuditLog.objects.get(target_id=instance.pk)
        assert entry.changes == {"name": {"old": "Old", "new": "New"}}

    def _make_serializer(
        self, actor: Any, validated_data: dict[str, Any] | None = None
    ) -> MagicMock:
        serializer = MagicMock()
        request = MagicMock()
        request.user = actor
        request.auth = {"tenant_id": str(uuid.uuid4())}
        serializer.context = {"request": request}
        serializer.Meta.model._meta.label_lower = "tenants.team"
        serializer._validated_data = validated_data or {}
        return serializer

    def _make_instance(self, **attrs: Any) -> MagicMock:
        instance = MagicMock()
        instance.pk = uuid.uuid4()
        for key, value in attrs.items():
            setattr(instance, key, value)
        return instance


@pytest.mark.django_db
class TestAuditViewSetPluginOnPostDestroy:
    def test_records_delete_action(self) -> None:
        from apps.sys_audit.plugins import AuditViewSetPlugin

        user = UserFactory()
        plugin = AuditViewSetPlugin()
        viewset = self._make_viewset(user)
        instance = self._make_instance()

        plugin.on_post_destroy(viewset, instance)

        entry = AuditLog.objects.get(target_id=instance.pk)
        assert entry.action == "delete"
        assert entry.changes == {}

    def _make_viewset(self, actor: Any) -> MagicMock:
        viewset = MagicMock()
        viewset.request.user = actor
        viewset.request.auth = {"tenant_id": str(uuid.uuid4())}
        return viewset

    def _make_instance(self) -> MagicMock:
        instance = MagicMock()
        instance.pk = uuid.uuid4()
        instance._meta.label_lower = "tenants.team"
        type(instance)._meta = MagicMock(label_lower="tenants.team")
        return instance
