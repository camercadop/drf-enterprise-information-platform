# Development Guide

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

```
drf-enterprise-information-platform/
  apps/           # Domain modules (identity, tenants, etc.)
  core/           # Framework foundations (base classes, utils, shared infrastructure)
    base/         # Base models, serializers, views
    exceptions/   # Custom exception hierarchy
    filters/      # Base filter classes
    pagination/   # Pagination classes
    permissions/  # Base permission classes
    utils/        # Shared utilities
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

### Type Safety

- All function parameters must have type annotations
- Use `X | None` instead of `Optional[X]`
- Avoid returning untyped values from typed functions

### Naming

- Files: lowercase with underscores (`base_serializer.py`)
- Classes: PascalCase (`BaseSerializer`)
- Plugins: PascalCase ending in `Plugin` (`SoftDeletablePlugin`)
- Template hooks: `pre_*`, `do_*`, `post_*`
- Plugin hooks: `on_pre_*`, `on_post_*`, `on_*`

### Models

- All tenant-scoped models inherit from `BaseModel` (includes timestamps + soft-delete + tenant FK)
- Use `CoreModel` for platform-level models that don't belong to a tenant
- All models use UUID as primary key (`primary_key=True`)
- Do not set `default_auto_field` in app configs
- Add a comment under each field explaining its purpose
- Soft-delete fields: `deleted_at`, `deleted_by`
- Timestamp fields: `created_at`, `updated_at`

### Serializers

- Inherit from `BaseSerializer`
- Use plugins for cross-cutting concerns
- Use template methods for per-serializer customization


## Docker

```bash
# Start all services
./docker-up.sh

# Or manually
docker compose up -d

# View logs
docker compose logs -f
```
