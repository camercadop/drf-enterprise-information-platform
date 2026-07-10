import os

os.environ.setdefault("DATABASE_URL", "postgresql://eip_user:eip_password@localhost:5432/eip_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from .base import *  # noqa: F403, F401, E402

DEBUG = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
