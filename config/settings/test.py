import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://eip_user:eip_password@localhost:5432/eip_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault(
    "CELERY_RESULT_BACKEND",
    "db+postgresql://eip_user:eip_password@localhost:5432/eip_test?options=-csearch_path%3Dasync_tasks",
)

from .base import *  # noqa: F403, F401, E402

DEBUG = True

CELERY_TASK_ALWAYS_EAGER = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# OpenTelemetry: disable exporters during tests to avoid noisy output
OTEL_EXPORTER = "none"

AUTH_MFA = {
    "ENCRYPTION_KEYS": ["test-encryption-key-for-tests-only"],
    "issuer": "Test Platform",
    "backup_code_count": 5,
    "backup_code_length": 8,
}
