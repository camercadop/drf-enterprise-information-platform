"""Redis client utility — raw redis-py access for modules that need Stream commands."""

import logging

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis:
    """Return a raw Redis client for commands not supported by the Django cache API.

    Use this when you need direct access to Redis commands unavailable through
    ``django.core.cache``. For standard cache operations (get, set, delete),
    use ``django.core.cache`` instead.

    Returns:
        A connected ``redis.Redis`` instance with ``decode_responses=True``.
    """
    url: str = settings.CACHES["default"]["LOCATION"]
    client: redis.Redis = redis.Redis.from_url(url, decode_responses=True)
    return client
