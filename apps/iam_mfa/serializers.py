import logging
from typing import Any

import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.iam_mfa.encryption import decrypt_secret
from apps.iam_mfa.models import MFABackupCode, MFADevice
from apps.tenants.utils import get_tenant_id, get_tenant_setting

logger = logging.getLogger(__name__)


class MFASetupSerializer(serializers.Serializer):
    """Generates a TOTP secret and QR code URI for MFA enrollment."""

    secret = serializers.CharField(read_only=True)
    qr_code = serializers.CharField(read_only=True)

    def save(self, **kwargs: Any) -> dict[str, str]:
        user = self.context["request"].user
        if MFADevice.objects.filter(user=user, is_active=True).exists():
            raise serializers.ValidationError(
                {"detail": "MFA is already active for this user."},
                code="mfa_already_active",
            )
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        issuer = settings.AUTH_MFA.get("issuer", "Enterprise Platform")
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=issuer,
        )

        qr_img = qrcode.make(provisioning_uri)
        qr_data_uri = self._qr_to_data_uri(qr_img)

        return {"secret": secret, "qr_code": qr_data_uri}

    @staticmethod
    def _qr_to_data_uri(qr_img: Any) -> str:
        import io

        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        import base64

        data_uri = (
            "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        )
        return data_uri


class MFAConfirmSetupSerializer(serializers.Serializer):
    """Confirms MFA enrollment by verifying a TOTP code against the client-held secret.

    The client receives the secret from MFASetupSerializer and submits it back
    alongside the TOTP code. The secret is verified before being encrypted and saved.
    """

    secret = serializers.CharField(write_only=True)
    code = serializers.CharField(write_only=True, min_length=6, max_length=6)
    label = serializers.CharField(
        write_only=True, required=False, default="Authenticator App"
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        totp = pyotp.TOTP(attrs["secret"])
        if not totp.verify(attrs["code"], valid_window=1):
            raise serializers.ValidationError(
                {"code": "Invalid authentication code."},
                code="mfa_invalid_code",
            )
        return attrs

    def save(self, **kwargs: Any) -> None:
        from apps.iam_mfa.encryption import encrypt_secret
        from apps.iam_mfa.signals import mfa_enabled
        from apps.tenants.models import Tenant
        from apps.tenants.utils import get_tenant_id

        request = self.context["request"]
        tenant_id = get_tenant_id(request)
        tenant = Tenant.objects.get(pk=tenant_id)
        MFADevice.objects.create(
            tenant=tenant,
            user=request.user,
            secret=encrypt_secret(self.validated_data["secret"]),
            label=self.validated_data["label"],
            is_active=True,
        )
        mfa_enabled.send(
            sender=self.__class__,
            user_id=str(request.user.pk),
            tenant_id=str(tenant_id),
        )
        logger.info(
            "MFA device enrolled: user_id=%s tenant_id=%s",
            request.user.pk,
            tenant_id,
        )


class MFAVerifySerializer(serializers.Serializer):
    """Verifies a TOTP code against the user's active MFA device."""

    code = serializers.CharField(write_only=True, min_length=6, max_length=6)

    def validate_code(self, value: str) -> str:
        user = self.context["request"].user
        device = MFADevice.objects.filter(user=user, is_active=True).first()
        if not device:
            raise serializers.ValidationError(
                "No active MFA device found.", code="mfa_not_setup"
            )

        secret = decrypt_secret(device.secret)
        totp = pyotp.TOTP(secret)
        if not totp.verify(value, valid_window=1):
            raise serializers.ValidationError(
                "Invalid authentication code.", code="mfa_invalid_code"
            )
        return value

    def save(self, **kwargs: Any) -> None:
        pass


class MFADisableSerializer(serializers.Serializer):
    """Disables MFA after verifying the user's TOTP code."""

    code = serializers.CharField(write_only=True, min_length=6, max_length=6)

    def validate_code(self, value: str) -> str:
        user = self.context["request"].user
        device = MFADevice.objects.filter(user=user, is_active=True).first()
        if not device:
            raise serializers.ValidationError(
                "No active MFA device found.", code="mfa_not_setup"
            )

        secret = decrypt_secret(device.secret)
        totp = pyotp.TOTP(secret)
        if not totp.verify(value, valid_window=1):
            raise serializers.ValidationError(
                "Invalid authentication code.", code="mfa_invalid_code"
            )
        return value

    def save(self, **kwargs: Any) -> None:
        from apps.tenants.utils import get_tenant_id

        request = self.context["request"]
        user = request.user
        device = MFADevice.objects.filter(user=user, is_active=True).first()
        if device:
            device.is_active = False
            device.save(update_fields=["is_active"])
            MFABackupCode.objects.filter(mfa_device=device).delete()
            logger.info(
                "MFA disabled: user_id=%s tenant_id=%s",
                user.pk,
                get_tenant_id(request),
            )


class MFABackupCodeSerializer(serializers.Serializer):
    """Generates and stores hashed backup codes for MFA recovery."""

    codes = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )

    def save(self, **kwargs: Any) -> dict[str, list[str]]:
        user = self.context["request"].user
        device = MFADevice.objects.filter(user=user, is_active=True).first()
        if not device:
            raise serializers.ValidationError(
                {"detail": "No active MFA device found."},
                code="mfa_not_setup",
            )

        count = settings.AUTH_MFA.get("backup_code_count", 10)
        length = settings.AUTH_MFA.get("backup_code_length", 10)

        import secrets
        import string

        characters = string.ascii_uppercase + string.digits
        raw_codes = [
            "".join(secrets.choice(characters) for _ in range(length))
            for _ in range(count)
        ]

        MFABackupCode.objects.filter(mfa_device=device).delete()
        for raw_code in raw_codes:
            MFABackupCode.objects.create(
                mfa_device=device,
                code_hash=make_password(raw_code),
            )

        return {"codes": raw_codes}


class MFAStatusSerializer(serializers.Serializer):
    """Returns the user's MFA status."""

    mfa_enabled = serializers.BooleanField(read_only=True)
    mfa_enforcement = serializers.CharField(read_only=True)
    device_label = serializers.CharField(read_only=True, allow_null=True)
    backup_codes_remaining = serializers.IntegerField(read_only=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        user = self.context["request"].user
        tenant_id = get_tenant_id(self.context["request"]) or ""

        mfa_enabled = get_tenant_setting(tenant_id, "mfa_enabled") == "true"
        mfa_enforcement = get_tenant_setting(tenant_id, "mfa_enforcement") or "optional"

        device = MFADevice.objects.filter(user=user, is_active=True).first()
        backup_count = (
            MFABackupCode.objects.filter(mfa_device=device, is_used=False).count()
            if device
            else 0
        )

        return {
            "mfa_enabled": mfa_enabled,
            "mfa_enforcement": mfa_enforcement,
            "device_label": device.label if device else None,
            "backup_codes_remaining": backup_count,
        }


class MFALoginVerifySerializer(serializers.Serializer):
    """Verifies a TOTP code or backup code against an MFA challenge token.

    Accepts a challenge token issued by LoginSerializer and a 6-digit TOTP code
    or a backup code. On success, issues a real JWT token pair with tenant context.
    Use this endpoint instead of the standard login endpoint when mfa_required is true.
    """

    challenge_token = serializers.CharField(write_only=True)
    code = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        from django.contrib.auth import get_user_model
        from django.contrib.auth.hashers import check_password
        from rest_framework_simplejwt.tokens import RefreshToken

        from apps.iam_mfa.encryption import decrypt_secret
        from apps.iam_mfa.services import verify_challenge_token
        from apps.iam_mfa.signals import mfa_verified

        claims = verify_challenge_token(attrs["challenge_token"])
        user_id = claims["user_id"]
        tenant_id = claims["tenant_id"]

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as err:
            raise serializers.ValidationError(
                {"challenge_token": "Invalid challenge token."},
                code="mfa_challenge_invalid",
            ) from err

        device = MFADevice.objects.filter(
            user=user, tenant_id=tenant_id, is_active=True
        ).first()
        if not device:
            raise serializers.ValidationError(
                {"detail": "No active MFA device found."},
                code="mfa_not_setup",
            )

        code = attrs["code"]
        totp_valid = pyotp.TOTP(decrypt_secret(device.secret)).verify(
            code, valid_window=1
        )

        if not totp_valid:
            # Try backup codes
            backup_valid = False
            matched_backup = None
            for b in MFABackupCode.objects.filter(mfa_device=device, is_used=False):
                if check_password(code, b.code_hash):
                    backup_valid = True
                    matched_backup = b
                    break

            if not backup_valid:
                logger.warning(
                    "MFA verification failed: user_id=%s tenant_id=%s",
                    user_id,
                    tenant_id,
                )
                raise serializers.ValidationError(
                    {"code": "Invalid authentication code."},
                    code="mfa_invalid_code",
                )

            matched_backup.is_used = True  # type: ignore[union-attr]
            matched_backup.save(update_fields=["is_used"])  # type: ignore[union-attr]
            logger.info(
                "MFA backup code used: user_id=%s tenant_id=%s",
                user_id,
                tenant_id,
            )

        mfa_verified.send(sender=self.__class__, user_id=user_id, tenant_id=tenant_id)

        refresh = RefreshToken.for_user(user)
        refresh["tenant_id"] = tenant_id

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "tenant_id": tenant_id,
            },
        }
