"""Celery application entry point."""

import os

from celery import Celery

from core.telemetry.setup import configure_telemetry

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

configure_telemetry()

app = Celery("eip", backend="core.celery.backend.TaskResultBackend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
