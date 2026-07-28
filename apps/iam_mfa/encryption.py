import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def _get_fernet() -> MultiFernet:
    """Build a MultiFernet instance from configured encryption keys.

    Reads AUTH_MFA["ENCRYPTION_KEYS"] (list of strings). The first key is used
    for encryption; all keys are tried for decryption, enabling zero-downtime
    key rotation by prepending a new key to the list.

    Raises:
        ImproperlyConfigured: If AUTH_MFA["ENCRYPTION_KEYS"] is missing or empty.
    """
    keys: list[str] = settings.AUTH_MFA.get("ENCRYPTION_KEYS", [])
    if not keys:
        raise ImproperlyConfigured(
            "AUTH_MFA['ENCRYPTION_KEYS'] must be a non-empty list"
        )
    fernets = [
        Fernet(base64.urlsafe_b64encode(hashlib.sha256(k.encode()).digest()))
        for k in keys
    ]
    return MultiFernet(fernets)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext MFA secret.

    Args:
        plaintext: The raw TOTP secret to encrypt.

    Returns:
        A Fernet-encrypted, URL-safe base64-encoded ciphertext string.
    """
    return str(_get_fernet().encrypt(plaintext.encode()).decode())


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a previously encrypted MFA secret.

    Tries all configured keys in order, supporting key rotation without
    re-encrypting existing secrets immediately.

    Args:
        ciphertext: The encrypted secret produced by encrypt_secret.

    Returns:
        The original plaintext secret.

    Raises:
        InvalidToken: If no configured key can decrypt the ciphertext.
    """
    try:
        return str(_get_fernet().decrypt(ciphertext.encode()).decode())
    except InvalidToken:
        logger.warning(
            "MFA secret decryption failed — token invalid or no matching key"
        )
        raise
