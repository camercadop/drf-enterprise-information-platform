import pyotp
import pytest
from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_mfa.encryption import encrypt_secret
from apps.iam_mfa.models import MFABackupCode, MFADevice
from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.iam_mfa import MFADeviceFactory


class TestMFAVerifyView(BaseActionAPITest):
    url = "/api/mfa/verify/"

    def _make_device(self) -> tuple[MFADevice, str]:
        raw_secret = pyotp.random_base32()
        device = MFADeviceFactory(
            user=self.user,
            tenant=self.membership.tenant,
            secret=encrypt_secret(raw_secret),
        )
        return device, raw_secret

    def test_smoke(self) -> None:
        response = self.client.post(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_valid_code_returns_200(self) -> None:
        _, raw_secret = self._make_device()
        code = pyotp.TOTP(raw_secret).now()
        response = self.client.post(self.url, {"code": code}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_code_returns_400(self) -> None:
        self._make_device()
        response = self.client.post(self.url, {"code": "000000"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["code"][0].code == "mfa_invalid_code"

    def test_no_device_returns_400(self) -> None:
        response = self.client.post(self.url, {"code": "123456"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["code"][0].code == "mfa_not_setup"


class TestMFADisableView(BaseActionAPITest):
    url = "/api/mfa/disable/"

    def _make_device(self) -> tuple[MFADevice, str]:
        raw_secret = pyotp.random_base32()
        device = MFADeviceFactory(
            user=self.user,
            tenant=self.membership.tenant,
            secret=encrypt_secret(raw_secret),
        )
        return device, raw_secret

    def test_smoke(self) -> None:
        response = self.client.post(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_valid_code_disables_device(self) -> None:
        device, raw_secret = self._make_device()
        code = pyotp.TOTP(raw_secret).now()
        response = self.client.post(self.url, {"code": code}, format="json")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        device.refresh_from_db()
        assert device.is_active is False

    def test_disable_deletes_backup_codes(self) -> None:
        device, raw_secret = self._make_device()
        MFABackupCode.objects.create(
            mfa_device=device, code_hash=make_password("BACKUP01"), is_used=False
        )
        code = pyotp.TOTP(raw_secret).now()
        self.client.post(self.url, {"code": code}, format="json")
        assert MFABackupCode.objects.filter(mfa_device=device).count() == 0

    def test_invalid_code_returns_400(self) -> None:
        self._make_device()
        response = self.client.post(self.url, {"code": "000000"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["code"][0].code == "mfa_invalid_code"


class TestMFABackupCodesView(BaseActionAPITest):
    url = "/api/mfa/backup-codes/"

    def test_smoke(self) -> None:
        response = self.client.post(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_generates_backup_codes(self) -> None:
        MFADeviceFactory(user=self.user, tenant=self.membership.tenant)
        response = self.client.post(self.url, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()["data"]
        assert "codes" in data
        assert len(data["codes"]) > 0

    def test_no_device_returns_400(self) -> None:
        response = self.client.post(self.url, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_regenerating_replaces_old_codes(self) -> None:
        device = MFADeviceFactory(user=self.user, tenant=self.membership.tenant)
        MFABackupCode.objects.create(
            mfa_device=device, code_hash=make_password("OLD01"), is_used=False
        )
        self.client.post(self.url, format="json")
        assert not MFABackupCode.objects.filter(
            mfa_device=device, code_hash=make_password("OLD01")
        ).exists()


class TestMFAStatusView(BaseActionAPITest):
    url = "/api/mfa/status/"
    http_method = "get"

    def test_smoke(self) -> None:
        response = self.client.get(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_returns_status_without_device(self) -> None:
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["device_label"] is None
        assert data["backup_codes_remaining"] == 0

    def test_returns_status_with_active_device(self) -> None:
        device = MFADeviceFactory(
            user=self.user, tenant=self.membership.tenant, label="My Phone"
        )
        MFABackupCode.objects.create(
            mfa_device=device, code_hash=make_password("CODE01"), is_used=False
        )
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["device_label"] == "My Phone"
        assert data["backup_codes_remaining"] == 1
