"""Config package — loads the Celery app alongside Django."""

from .celery import app as celery_app

__all__ = ["celery_app"]
