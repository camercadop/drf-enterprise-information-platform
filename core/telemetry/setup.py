"""
OpenTelemetry instrumentation setup for DRF Enterprise Information Platform.

This module provides the bootstrap code for OpenTelemetry instrumentation,
including resource configuration, exporter setup, tracer/meter providers,
and instrument() calls for Django, psycopg2, Redis, and Celery.
"""

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    MetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME as OTEL_SERVICE_NAME_KEY
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)

logger = logging.getLogger(__name__)

SERVICE_NAME = os.environ.get(
    "OTEL_SERVICE_NAME", "drf-enterprise-information-platform"
)


def configure_telemetry() -> None:
    """
    Configure OpenTelemetry instrumentation for the application.

    This function sets up the OpenTelemetry SDK with the appropriate
    exporters based on the environment configuration.
    """
    try:
        # Create resource with service name
        resource = Resource.create(
            {
                OTEL_SERVICE_NAME_KEY: SERVICE_NAME,
            }
        )

        # Configure trace provider
        trace_provider = TracerProvider(resource=resource)

        # Configure span exporter based on environment
        span_exporter = _get_span_exporter()
        if span_exporter:
            trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))

        trace.set_tracer_provider(trace_provider)

        # Configure metric provider
        metric_provider = MeterProvider(resource=resource)

        # Configure metric exporter based on environment
        metric_exporter = _get_metric_exporter()
        if metric_exporter:
            metric_provider.add_metric_reader(
                PeriodicExportingMetricReader(metric_exporter)
            )

        metrics.set_meter_provider(metric_provider)

        logger.info("OpenTelemetry instrumentation configured successfully")

    except Exception as e:
        logger.error(f"Failed to configure OpenTelemetry: {e}")
        raise


def _get_span_exporter() -> SpanExporter | None:
    """
    Get the appropriate span exporter based on environment configuration.

    Returns:
        SpanExporter: The configured span exporter or None if disabled.
    """
    from django.conf import settings

    exporter_type = getattr(settings, "OTEL_EXPORTER", "console")

    if exporter_type == "none":
        return None
    elif exporter_type == "console":
        return ConsoleSpanExporter()
    elif exporter_type == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        endpoint = getattr(
            settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"
        )
        return OTLPSpanExporter(endpoint=endpoint)
    else:
        logger.warning(
            f"Unknown span exporter type: {exporter_type}, defaulting to console"
        )
        return ConsoleSpanExporter()


def _get_metric_exporter() -> MetricExporter | None:
    """
    Get the appropriate metric exporter based on environment configuration.

    Returns:
        MetricExporter: The configured metric exporter or None if disabled.
    """
    from django.conf import settings

    exporter_type = getattr(settings, "OTEL_EXPORTER", "console")

    if exporter_type == "none":
        return None
    elif exporter_type == "console":
        return ConsoleMetricExporter()
    elif exporter_type == "otlp":
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )

        endpoint = getattr(
            settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"
        )
        return OTLPMetricExporter(endpoint=endpoint)
    else:
        logger.warning(
            f"Unknown metric exporter type: {exporter_type}, defaulting to console"
        )
        return ConsoleMetricExporter()


def instrument() -> None:
    """
    Instrument Django, psycopg2, Redis, and Celery for OpenTelemetry.

    This function should be called after configure_telemetry() to enable
    instrumentation for the supported libraries.
    """
    try:
        # Import and configure instrumentation for supported libraries
        from opentelemetry.instrumentation.django import DjangoInstrumentor

        DjangoInstrumentor().instrument()

        # Instrument psycopg2
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        Psycopg2Instrumentor().instrument()

        # Instrument Redis
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()

        # Instrument Celery
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()

        logger.info("All OpenTelemetry instrumentors configured successfully")

    except ImportError as e:
        logger.error(f"Failed to import OpenTelemetry instrumentation: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to instrument libraries: {e}")
        raise
