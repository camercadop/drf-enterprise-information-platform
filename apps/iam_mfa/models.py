from django.conf import settings
from django.db import models

from apps.tenants.models import TenantAwareModel
from core.base.models import BaseModel


class MFADevice(TenantAwareModel):
    """A TOTP-based MFA device enrolled by a user within a tenant."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa_devices",
    )
    # The user this MFA device belongs to

    secret = models.TextField()
    # The encrypted TOTP secret (encrypted at rest using Fernet)

    label = models.CharField(max_length=255)
    # Human-readable label for the device (e.g., "Authenticator App")

    is_active = models.BooleanField(default=True)
    # Whether this device is currently active and can be used for MFA challenges

    class Meta:
        db_table = "iam_mfa_devices"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"MFADevice({self.user_id}, {self.label})"


class MFABackupCode(BaseModel):
    """A single-use backup code for MFA recovery, stored as a hash."""

    mfa_device = models.ForeignKey(
        MFADevice,
        on_delete=models.CASCADE,
        related_name="backup_codes",
    )
    # The MFA device this backup code belongs to

    code_hash = models.CharField(max_length=255)
    # Hashed backup code (never stored in plaintext)

    is_used = models.BooleanField(default=False)
    # Whether this backup code has already been consumed

    class Meta:
        db_table = "iam_mfa_backup_codes"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"MFABackupCode({self.mfa_device_id}, used={self.is_used})"
