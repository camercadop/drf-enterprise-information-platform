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

# Run migrations
uv run python manage.py migrate

# Start development server
uv run python manage.py runserver
```

## Project Structure

Apps are grouped by naming convention. See [Architecture](architecture.md) for details.

```
drf-enterprise-information-platform/
  apps/           # Domain modules and infrastructure apps
  core/           # Framework foundations (base classes, utils, shared infrastructure)
    base/         # Base models, serializers, views
    exceptions/   # Custom exception hierarchy
    fields/       # Custom DRF serializer fields
    filters/      # Base filter classes
    pagination/   # Pagination classes
    permissions/  # Base permission classes
    utils/        # Shared utilities
    validators/   # Validation logic (model fields, functions, serializer-level)
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
./docker-up.sh

# Or manually
docker compose up -d

# View logs
docker compose logs -f
```
