"""Signals for the iam_auth app."""

from django.dispatch import Signal, receiver

from .lockout import clear_lockout, record_failed_attempt

login_failed = Signal()
# Sent when a login attempt fails due to invalid credentials.
# Provides: email (str)

password_changed = Signal()
# Sent when a user successfully changes their password.
# Provides: email (str)


@receiver(login_failed)
def handle_login_failed(sender: object, email: str, **kwargs: object) -> None:
    """Record a failed login attempt and lock the account if threshold is reached.

    Args:
        sender: The sender of the signal (unused).
        email: The email address that failed authentication.
    """
    record_failed_attempt(email)


@receiver(password_changed)
def handle_password_changed(sender: object, email: str, **kwargs: object) -> None:
    """Clear lockout state when a user successfully changes their password.

    Args:
        sender: The sender of the signal (unused).
        email: The email address whose lockout state should be cleared.
    """
    clear_lockout(email)
