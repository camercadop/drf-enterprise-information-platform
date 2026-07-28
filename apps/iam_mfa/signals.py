import logging

from django.dispatch import Signal

logger = logging.getLogger(__name__)

mfa_enabled = Signal()
# Sent when a user successfully enrolls an MFA device.
# Provides: user_id (UUID), tenant_id (UUID)

mfa_disabled = Signal()
# Sent when a user disables their MFA device.
# Provides: user_id (UUID), tenant_id (UUID)

mfa_verified = Signal()
# Sent when a user successfully verifies a TOTP code.
# Provides: user_id (UUID), tenant_id (UUID)

backup_codes_generated = Signal()
# Sent when new backup codes are generated for a user.
# Provides: user_id (UUID), tenant_id (UUID), count (int)
