import uuid

from django.conf import settings
from django.db import models

PASSWORD_HISTORY_LIMIT = 5
# Number of recent passwords to check against when changing password


class UserPasswordHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique identifier for the history entry

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_history",
    )
    # The user this password belonged to

    hashed_password = models.CharField(max_length=255)
    # The hashed password (never stored in plaintext)

    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when this password was set

    class Meta:
        db_table = "auth_password_history"
        ordering = ["-created_at"]
        verbose_name_plural = "user password histories"

    def __str__(self) -> str:
        return f"UserPasswordHistory({self.user_id}, {self.created_at})"
