"""Integration tests for the tenant settings API endpoints."""

from contextlib import contextmanager
from typing import Any, Generator
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_users.models import TenantMembership
from apps.tenants.models import TenantSetting

URL = "/api/tenant-settings/"

MOCK_CATALOG: dict[str, dict[str, Any]] = {
    "max_users": {
        "label": "Max users",
        "namespace": "limits",
        "type": "integer",
        "default": "10",
        "schema": {"type": "integer", "minimum": 1},
    },
    "feature_flag": {
        "label": "Feature flag",
        "namespace": "features",
        "type": "boolean",
        "default": "false",
    },
    "secret_key": {
        "label": "Secret key",
        "namespace": "security",
        "type": "string",
        "default": "",
        "private": True,
    },
}


@contextmanager
def _patch_catalog() -> Generator[None, None, None]:
    """Patch catalog in both views and serializers."""
    with patch(
        "apps.tenant_settings.views.get_merged_catalog",
        return_value=MOCK_CATALOG,
    ), patch(
        "apps.tenant_settings.serializers.get_merged_catalog",
        return_value=MOCK_CATALOG,
    ):
        yield


def _make_setting(membership: TenantMembership, key: str, value: str) -> TenantSetting:
    return TenantSetting.objects.create(
        tenant=membership.tenant,
        key=key,
        value=value,
    )


@pytest.mark.django_db
class TestTenantSettingList:
    """Tests for GET /api/tenant-settings/."""

    def test_smoke(self, auth_client: APIClient) -> None:
        """Verify the list endpoint is reachable and does not crash."""
        with _patch_catalog():
            response = auth_client.get(URL)
        assert response.status_code // 100 in (2, 4)

    def test_list_success(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """List returns 200 with existing settings."""
        _make_setting(membership, "max_users", "10")
        with _patch_catalog():
            response = auth_client.get(URL)
        assert response.status_code == status.HTTP_200_OK

    def test_private_settings_excluded(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Private settings must not appear in list responses."""
        _make_setting(membership, "secret_key", "s3cr3t")
        with _patch_catalog():
            response = auth_client.get(URL)
        assert response.status_code == status.HTTP_200_OK
        keys = [item["key"] for item in response.json()["data"]]
        assert "secret_key" not in keys

    def test_list_includes_namespace(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """List response must include namespace derived from catalog."""
        _make_setting(membership, "max_users", "10")
        with _patch_catalog():
            response = auth_client.get(URL)
        assert response.status_code == status.HTTP_200_OK
        result = next(
            r for r in response.json()["data"] if r["key"] == "max_users"
        )
        assert result["namespace"] == "limits"


@pytest.mark.django_db
class TestTenantSettingRetrieve:
    """Tests for GET /api/tenant-settings/{key}/."""

    def test_smoke(self, auth_client: APIClient) -> None:
        """Verify the retrieve endpoint is reachable and does not crash."""
        with _patch_catalog():
            response = auth_client.get(f"{URL}nonexistent_key/")
        assert response.status_code // 100 in (2, 4)

    def test_retrieve_success(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Retrieve an existing setting by key returns 200."""
        _make_setting(membership, "max_users", "10")
        with _patch_catalog():
            response = auth_client.get(f"{URL}max_users/")
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_includes_namespace(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Retrieve response must include namespace derived from catalog."""
        _make_setting(membership, "max_users", "10")
        with _patch_catalog():
            response = auth_client.get(f"{URL}max_users/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["namespace"] == "limits"

    def test_private_setting_returns_404(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Private settings must not be retrievable via the API."""
        _make_setting(membership, "secret_key", "s3cr3t")
        with _patch_catalog():
            response = auth_client.get(f"{URL}secret_key/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTenantSettingUpdate:
    """Tests for PATCH /api/tenant-settings/{key}/."""

    @pytest.fixture(autouse=True)
    def _setup(self, auth_client: APIClient, membership: TenantMembership) -> None:
        membership.is_admin = True
        membership.save()
        self.client = auth_client
        self.membership = membership

    def test_smoke(self) -> None:
        """Verify the update endpoint is reachable and does not crash."""
        with _patch_catalog():
            response = self.client.patch(f"{URL}nonexistent_key/", {}, format="json")
        assert response.status_code // 100 in (2, 4)

    def test_partial_update_valid_value(self) -> None:
        """PATCH with a valid value updates the setting."""
        _make_setting(self.membership, "max_users", "10")
        with _patch_catalog():
            response = self.client.patch(
                f"{URL}max_users/", {"value": "20"}, format="json"
            )
        assert response.status_code == status.HTTP_200_OK
        assert (
            TenantSetting.objects.get(
                key="max_users", tenant=self.membership.tenant
            ).value
            == "20"
        )

    def test_partial_update_invalid_type_returns_400(self) -> None:
        """PATCH with a value that fails type coercion returns 400."""
        _make_setting(self.membership, "max_users", "10")
        with _patch_catalog():
            response = self.client.patch(
                f"{URL}max_users/", {"value": "not_an_int"}, format="json"
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "value" in response.data["data"]

    def test_partial_update_schema_violation_returns_400(self) -> None:
        """PATCH with a value that violates JSON Schema returns 400."""
        _make_setting(self.membership, "max_users", "10")
        with _patch_catalog():
            response = self.client.patch(
                f"{URL}max_users/", {"value": "0"}, format="json"
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "value" in response.data["data"]

    def test_put_is_not_allowed(self) -> None:
        """PUT must return 405 — only PATCH is supported."""
        _make_setting(self.membership, "max_users", "10")
        with _patch_catalog():
            response = self.client.put(
                f"{URL}max_users/", {"value": "20"}, format="json"
            )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestTenantSettingPermissions:
    """Tests for TenantSetting write permission enforcement."""

    def test_non_admin_cannot_update_setting(
        self, auth_client: APIClient, membership: TenantMembership
    ) -> None:
        """Regular members cannot update settings."""
        _make_setting(membership, "max_users", "10")
        with _patch_catalog():
            response = auth_client.patch(
                f"{URL}max_users/", {"value": "20"}, format="json"
            )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access_settings(
        self, api_client: APIClient
    ) -> None:
        """Unauthenticated requests must be rejected."""
        response = api_client.get(URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
