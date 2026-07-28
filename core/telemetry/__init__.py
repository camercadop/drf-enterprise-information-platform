"""
OpenTelemetry instrumentation.

This module provides OpenTelemetry instrumentation for Django, psycopg2, Redis, and Celery.
It enables distributed tracing and metrics collection across the application.
"""

from .setup import configure_telemetry

__all__ = ["configure_telemetry"]
