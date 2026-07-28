import pyotp
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_mfa.encryption import encrypt_secret
from apps.iam_mfa.models import MFADevice
from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.iam_mfa import MFADeviceFactory


class TestMFASetupView(BaseActionAPITest):
    url = "/api/mfa/setup/"
    http_method = "get"

    def test_smoke(self) -> None:
        response = self.client.get(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_returns_secret_and_qr_code(self) -> None:
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "secret" in data
        assert "qr_code" in data
        assert data["qr_code"].startswith("data:image/png;base64,")

    def test_returns_400_when_device_already_active(self) -> None:
        MFADeviceFactory(user=self.user, tenant=self.membership.tenant)
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestMFAConfirmSetupView(BaseActionAPITest):
    url = "/api/mfa/confirm-setup/"

    def test_smoke(self) -> None:
        response = self.client.post(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_valid_secret_and_code_creates_device(self) -> None:
        raw_secret = pyotp.random_base32()
        code = pyotp.TOTP(raw_secret).now()
        response = self.client.post(
            self.url,
            {"secret": raw_secret, "code": code, "label": "My App"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert MFADevice.objects.filter(user=self.user, is_active=True).exists()

    def test_device_secret_is_encrypted_at_rest(self) -> None:
        raw_secret = pyotp.random_base32()
        code = pyotp.TOTP(raw_secret).now()
        self.client.post(
            self.url,
            {"secret": raw_secret, "code": code},
            format="json",
        )
        device = MFADevice.objects.get(user=self.user)
        assert device.secret != raw_secret

    def test_invalid_code_returns_400(self) -> None:
        raw_secret = pyotp.random_base32()
        response = self.client.post(
            self.url,
            {"secret": raw_secret, "code": "000000"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["code"][0].code == "mfa_invalid_code"

    def test_missing_secret_returns_400(self) -> None:
        response = self.client.post(self.url, {"code": "123456"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "secret" in response.data["data"]

    def test_mfa_enabled_signal_is_fired(self) -> None:
        from unittest.mock import patch
        from apps.iam_mfa.signals import mfa_enabled

        raw_secret = pyotp.random_base32()
        code = pyotp.TOTP(raw_secret).now()
        with patch.object(mfa_enabled, "send") as mock_send:
            self.client.post(
                self.url,
                {"secret": raw_secret, "code": code},
                format="json",
            )
            mock_send.assert_called_once()
