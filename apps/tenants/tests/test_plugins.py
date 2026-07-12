"""Tests for TenantInjectionSerializerPlugin."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from apps.tenants.plugins import TenantInjectionSerializerPlugin
from core.exceptions.api import PermissionDeniedError


class TestOnPreCreate:
    """Tests for tenant injection during create operations."""

    def _make_serializer(
        self, *, has_tenant: bool = True, tenant_id: str | None = "tenant-uuid"
    ) -> MagicMock:
        serializer = MagicMock()
        model = MagicMock()
        if has_tenant:
            model.tenant_id = None
        else:
            del model.tenant_id
        serializer.Meta.model = model
        request = MagicMock()
        if tenant_id:
            request.auth = {"tenant_id": tenant_id}
        else:
            request.auth = None
        serializer.context = {"request": request}
        return serializer

    def test_injects_tenant_id_from_jwt(self) -> None:
        plugin = TenantInjectionSerializerPlugin()
        serializer = self._make_serializer(tenant_id="abc-123")
        data: dict[str, Any] = {}

        plugin.on_pre_create(serializer, data)

        assert data["tenant_id"] == "abc-123"

    def test_raises_when_no_tenant_claim(self) -> None:
        plugin = TenantInjectionSerializerPlugin()
        serializer = self._make_serializer(tenant_id=None)

        with pytest.raises(PermissionDeniedError, match="No tenant context"):
            plugin.on_pre_create(serializer, {})

    def test_skips_model_without_tenant_field(self) -> None:
        plugin = TenantInjectionSerializerPlugin()
        serializer = self._make_serializer(has_tenant=False, tenant_id="abc-123")
        data: dict[str, Any] = {}

        plugin.on_pre_create(serializer, data)

        assert "tenant_id" not in data

    def test_raises_when_no_request_in_context(self) -> None:
        plugin = TenantInjectionSerializerPlugin()
        serializer = MagicMock()
        serializer.Meta.model = MagicMock()
        serializer.Meta.model.tenant_id = None
        serializer.context = {}

        with pytest.raises(PermissionDeniedError, match="No tenant context"):
            plugin.on_pre_create(serializer, {})


class TestOnPreUpdate:
    """Tests for tenant boundary enforcement during update operations."""

    def _make_serializer(self, *, has_tenant: bool = True) -> MagicMock:
        serializer = MagicMock()
        model = MagicMock()
        if has_tenant:
            model.tenant_id = None
        else:
            del model.tenant_id
        serializer.Meta.model = model
        return serializer

    def _make_instance(self, tenant_id: str = "current-tenant") -> MagicMock:
        instance = MagicMock()
        instance.tenant_id = tenant_id
        return instance

    def test_strips_matching_tenant_id(self) -> None:
        plugin = TenantInjectionSerializerPlugin()
        serializer = self._make_serializer()
        instance = self._make_instance("current-tenant")
        data: dict[str, Any] = {"tenant_id": "current-tenant", "name": "Updated"}

        plugin.on_pre_update(serializer, instance, data)

        assert "tenant_id" not in data
        assert data["name"] == "Updated"

    def test_raises_on_tenant_reassignment(self) -> None:
        plugin = TenantInjectionSerializerPlugin()
        serializer = self._make_serializer()
        instance = self._make_instance("current-tenant")
        data: dict[str, Any] = {"tenant_id": "different-tenant"}

        with pytest.raises(PermissionDeniedError, match="Tenant reassignment"):
            plugin.on_pre_update(serializer, instance, data)

    def test_skips_model_without_tenant_field(self) -> None:
        plugin = TenantInjectionSerializerPlugin()
        serializer = self._make_serializer(has_tenant=False)
        instance = MagicMock()
        data: dict[str, Any] = {"tenant_id": "something"}

        plugin.on_pre_update(serializer, instance, data)

        assert data["tenant_id"] == "something"

    def test_noop_when_tenant_id_not_in_data(self) -> None:
        plugin = TenantInjectionSerializerPlugin()
        serializer = self._make_serializer()
        instance = self._make_instance("current-tenant")
        data: dict[str, Any] = {"name": "Updated"}

        plugin.on_pre_update(serializer, instance, data)

        assert data == {"name": "Updated"}
