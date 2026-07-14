"""Tests for sys_audit model append-only enforcement."""

import pytest

from apps.sys_audit.models import AuditLog
from tests.factories.users import UserFactory


@pytest.mark.django_db
class TestAuditLogAppendOnly:
    def _create_audit(self) -> AuditLog:
        user = UserFactory()
        return AuditLog.objects.create(
            actor=user,
            action="create",
            target_type="tenants.team",
            target_id=user.pk,
            changes={"name": "Test"},
        )

    def test_create_succeeds(self) -> None:
        entry = self._create_audit()
        assert entry.pk is not None
        assert entry.action == "create"

    def test_save_on_existing_raises(self) -> None:
        entry = self._create_audit()
        entry.action = "update"
        with pytest.raises(NotImplementedError, match="immutable"):
            entry.save()

    def test_delete_on_instance_raises(self) -> None:
        entry = self._create_audit()
        with pytest.raises(NotImplementedError, match="cannot be deleted"):
            entry.delete()

    def test_manager_update_raises(self) -> None:
        self._create_audit()
        with pytest.raises(NotImplementedError, match="immutable"):
            AuditLog.objects.update(action="delete")

    def test_manager_delete_raises(self) -> None:
        self._create_audit()
        with pytest.raises(NotImplementedError, match="cannot be deleted"):
            AuditLog.objects.delete()
