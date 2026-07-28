# OpenTelemetry Integration

This directory contains the OpenTelemetry instrumentation setup for the DRF Enterprise Information Platform.

## Overview

OpenTelemetry is configured to instrument Django, psycopg2, Redis, and Celery. Both traces and metrics are enabled with configurable exporters per environment.

## Configuration

- **Development**: Console exporter
- **Test**: No exporter
- **Production**: OTLP exporter


## Files

- `setup.py`: Instrumentation bootstrap with resource, exporter, tracer/meter providers, and `instrument()` calls

## Usage

The telemetry is automatically configured when the application starts:
- From `asgi.py`
- From `wsgi.py`
- From `celery.py`

## Environment Variables

- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint for production
- `OTEL_*`: Various OpenTelemetry configuration options

## Metrics and Traces

Both traces and metrics are captured and can be viewed in the Grafana dashboard with Tempo (traces) and Prometheus (metrics).
