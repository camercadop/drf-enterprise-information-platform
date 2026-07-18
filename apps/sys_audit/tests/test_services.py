"""Tests for sys_audit.services.log_audit helper."""

import uuid

import pytest

from apps.sys_audit.models import AuditLog
from apps.sys_audit.services import log_audit
from tests.factories.tenants import TenantFactory
from tests.factories.users import UserFactory


@pytest.mark.django_db
class TestLogAudit:
    def test_creates_audit_record(self) -> None:
        user = UserFactory()
        tenant = TenantFactory()
        target_id = uuid.uuid4()

        entry = log_audit(
            actor=user,
            action="create",
            target_type="tenants.team",
            target_id=target_id,
            tenant_id=tenant.id,
            changes={"name": "Engineering"},
        )

        assert entry.pk is not None
        assert entry.actor == user
        assert entry.action == "create"
        assert entry.target_type == "tenants.team"
        assert entry.target_id == target_id
        assert entry.changes == {"name": "Engineering"}

    def test_tenant_id_nullable(self) -> None:
        user = UserFactory()

        entry = log_audit(
            actor=user,
            action="update",
            target_type="users.user",
            target_id=user.pk,
        )

        assert entry.tenant_id is None

    def test_changes_defaults_to_empty_dict(self) -> None:
        user = UserFactory()

        entry = log_audit(
            actor=user,
            action="delete",
            target_type="tenants.team",
            target_id=uuid.uuid4(),
        )

        assert entry.changes == {}

    def test_free_form_action(self) -> None:
        user = UserFactory()

        entry = log_audit(
            actor=user,
            action="password_change",
            target_type="users.user",
            target_id=user.pk,
        )

        assert entry.action == "password_change"

    def test_accepts_string_tenant_id(self) -> None:
        user = UserFactory()
        tenant = TenantFactory()
        tenant_id = str(tenant.id)

        entry = log_audit(
            actor=user,
            action="create",
            target_type="tenants.team",
            target_id=uuid.uuid4(),
            tenant_id=tenant_id,
        )

        assert str(entry.tenant_id) == tenant_id

    def test_persists_to_database(self) -> None:
        user = UserFactory()
        target_id = uuid.uuid4()

        log_audit(
            actor=user,
            action="create",
            target_type="tenants.team",
            target_id=target_id,
        )

        assert AuditLog.objects.filter(target_id=target_id).exists()
