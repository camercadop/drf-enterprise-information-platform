import pyotp
import pytest
from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.test import APIClient

from apps.iam_mfa.encryption import encrypt_secret
from apps.iam_mfa.models import MFABackupCode, MFADevice
from apps.iam_mfa.services import issue_challenge_token
from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest
from tests.factories.iam_mfa import MFADeviceFactory
from tests.factories.tenants import TenantMembershipFactory, TenantRoleFactory


LOGIN_URL = "/api/auth/login/"
LOGIN_VERIFY_URL = "/api/mfa/login-verify/"


class TestLoginWithMFA(BaseActionAPITest):
    url = LOGIN_URL

    @pytest.fixture(autouse=True)
    def _setup_base(self, api_client: APIClient, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = api_client
        self.user = user
        self.membership = membership

    def _login(self) -> dict:
        response = self.client.post(
            self.url, {"email": self.user.email, "password": "TestPass123!"}
        )
        return response

    def test_login_without_mfa_returns_tokens(self) -> None:
        response = self._login()
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "mfa_required" not in response.data

    def test_login_with_active_mfa_returns_challenge(self) -> None:
        MFADeviceFactory(user=self.user, tenant=self.membership.tenant)
        response = self._login()
        assert response.status_code == status.HTTP_200_OK
        assert response.data["mfa_required"] is True
        assert "challenge_token" in response.data
        assert "access" not in response.data

    def test_login_mfa_required_no_device_blocks_login(self) -> None:
        from apps.tenants.models import TenantSetting
        TenantSetting.objects.update_or_create(
            tenant=self.membership.tenant,
            key="mfa_enforcement",
            defaults={"value": "required"},
        )
        response = self._login()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["detail"][0].code == "mfa_setup_incomplete"


class TestMFALoginVerifyView(BaseActionAPITest):
    url = LOGIN_VERIFY_URL

    @pytest.fixture(autouse=True)
    def _setup_base(self, api_client: APIClient, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = api_client
        self.user = user
        self.membership = membership

    def _make_device(self) -> tuple[MFADevice, str]:
        raw_secret = pyotp.random_base32()
        device = MFADeviceFactory(
            user=self.user,
            tenant=self.membership.tenant,
            secret=encrypt_secret(raw_secret),
        )
        return device, raw_secret

    def _challenge_token(self) -> str:
        return issue_challenge_token(str(self.user.pk), str(self.membership.tenant_id))

    def test_smoke(self) -> None:
        response = self.client.post(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_valid_totp_returns_tokens(self) -> None:
        device, raw_secret = self._make_device()
        code = pyotp.TOTP(raw_secret).now()
        response = self.client.post(
            self.url,
            {"challenge_token": self._challenge_token(), "code": code},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["tenant_id"] == str(self.membership.tenant_id)

    def test_invalid_totp_returns_400(self) -> None:
        self._make_device()
        response = self.client.post(
            self.url,
            {"challenge_token": self._challenge_token(), "code": "000000"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["code"][0].code == "mfa_invalid_code"

    def test_valid_backup_code_returns_tokens(self) -> None:
        device, _ = self._make_device()
        raw_code = "BACKUPCODE1"
        MFABackupCode.objects.create(
            mfa_device=device, code_hash=make_password(raw_code), is_used=False
        )
        response = self.client.post(
            self.url,
            {"challenge_token": self._challenge_token(), "code": raw_code},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_backup_code_is_marked_used(self) -> None:
        device, _ = self._make_device()
        raw_code = "BACKUPCODE2"
        backup = MFABackupCode.objects.create(
            mfa_device=device, code_hash=make_password(raw_code), is_used=False
        )
        self.client.post(
            self.url,
            {"challenge_token": self._challenge_token(), "code": raw_code},
            format="json",
        )
        backup.refresh_from_db()
        assert backup.is_used is True

    def test_used_backup_code_is_rejected(self) -> None:
        device, _ = self._make_device()
        raw_code = "BACKUPCODE3"
        MFABackupCode.objects.create(
            mfa_device=device, code_hash=make_password(raw_code), is_used=True
        )
        response = self.client.post(
            self.url,
            {"challenge_token": self._challenge_token(), "code": raw_code},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_expired_challenge_token_returns_400(self) -> None:
        from datetime import UTC, datetime, timedelta
        import jwt as pyjwt
        from django.conf import settings as django_settings
        from apps.iam_mfa.services import _CHALLENGE_TYPE

        self._make_device()
        now = datetime.now(tz=UTC)
        expired_payload = {
            "user_id": str(self.user.pk),
            "tenant_id": str(self.membership.tenant_id),
            "type": _CHALLENGE_TYPE,
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=5),
        }
        expired_token = pyjwt.encode(expired_payload, django_settings.SECRET_KEY, algorithm="HS256")
        response = self.client.post(
            self.url,
            {"challenge_token": expired_token, "code": "123456"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_no_active_device_returns_400(self) -> None:
        response = self.client.post(
            self.url,
            {"challenge_token": self._challenge_token(), "code": "123456"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["data"]["detail"][0].code == "mfa_not_setup"

    def test_mfa_verified_signal_is_fired(self) -> None:
        from unittest.mock import patch
        from apps.iam_mfa.signals import mfa_verified

        device, raw_secret = self._make_device()
        code = pyotp.TOTP(raw_secret).now()
        with patch.object(mfa_verified, "send") as mock_send:
            self.client.post(
                self.url,
                {"challenge_token": self._challenge_token(), "code": code},
                format="json",
            )
            mock_send.assert_called_once()
