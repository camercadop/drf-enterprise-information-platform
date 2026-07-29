# Development Guide

How to work in this project — setup, commands, tooling, environment, and workflow. This file does not cover how code should look (see [Code Style](code-style.md)) or why things are designed the way they are (see [Architecture](architecture.md)).

## Prerequisites

- Python 3.14+
- Docker & Docker Compose
- uv (package manager)

## Setup

```bash
# Clone and enter the project
git clone <repository-url>
cd drf-enterprise-information-platform

# Start infrastructure
docker compose up -d

# Install dependencies
uv sync

# Create the async_tasks schema (required for Celery result backend)
psql $DATABASE_URL -f scripts/postgres/init.sql

# Run migrations
uv run python manage.py migrate

# Start development server
uv run python manage.py runserver
```

## Running the Celery Worker

In a separate terminal:

```bash
uv run celery -A config worker --loglevel=info
```

## Running Celery Beat

Required for the event bus consumer and any other periodic tasks. In a separate terminal:

```bash
uv run celery -A config beat --loglevel=info
```

## Project Structure

Apps are grouped by naming convention. See [Architecture](architecture.md) for details.

```
drf-enterprise-information-platform/
  apps/           # Domain modules and infrastructure apps
  core/           # Framework foundations (base classes, utils, shared infrastructure)
    base/         # Base classes for models, serializers, and views
    celery/       # Celery configuration and task infrastructure
    exceptions/   # Custom exception hierarchy and error handling
    fields/       # Custom DRF serializer fields
    filters/      # Reusable filter backends and base filter classes
    middleware/   # Cross-cutting request/response middleware
    openapi/      # OpenAPI schema generation and customization
    pagination/   # Pagination strategies and base classes
    permissions/  # Base permission classes and shared permission logic
    renderers/    # API response formatting and rendering
    serializers/  # Serializer base classes and plugin infrastructure
    telemetry/    # Observability setup (tracing, metrics)
    utils/        # Shared utility functions
    validators/   # Reusable validation logic for models, fields, and serializers
    module_resolver.py  # Runtime resolution of dotted-path class references
  config/         # Django settings, URLs, ASGI/WSGI
  docs/           # Documentation
  tests/          # Test suite
```

## Testing

See [Testing](testing.md) for full details on structure, fixtures, and conventions.

```bash
uv run pytest
```

## Code Quality

```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy .

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

## Conventions

See [Code Style](code-style.md) for all formatting, naming, and structural conventions.

## API Documentation

Interactive API docs are available at `/api/schema/swagger-ui/` (requires authentication). The raw OpenAPI schema is served at `/api/schema/`.


## Docker

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f
```
