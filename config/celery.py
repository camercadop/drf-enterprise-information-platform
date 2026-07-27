"""Celery application entry point."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("eip", backend="core.celery.backend.TaskResultBackend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
