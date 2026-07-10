# DRF Enterprise Information Platform

Multi-tenant enterprise platform built with Django REST Framework. Designed as a modular monolith with convention-over-configuration defaults, a plugin-based extensibility model, and security by default.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.14 |
| Framework | Django 6 + Django REST Framework |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Auth | JWT (simplejwt) with token blacklisting |
| Containers | Docker + Docker Compose |
| Quality | Ruff, mypy, pre-commit |
| Testing | Pytest, Factory Boy |
| CI | GitHub Actions |

## Key Features

### Data

- **Multi-tenancy** — shared database with tenant FK filtering, isolation at the permission layer
- **Soft-delete** — default deletion strategy with `deleted_at`/`deleted_by` fields

### Architecture

- **Plugin system** — stateless plugins for cross-cutting concerns on serializers
- **Template methods** — `pre_*/do_*/post_*` hooks for per-class customization

### API & Auth

- **Standard API envelope** — consistent `{status, data}` response format
- **JWT authentication** — short-lived access tokens, rotating refresh tokens, tenant context in claims

## Project Structure

```
apps/           # Domain modules (authentication, tenants, users)
core/           # Framework foundations (base classes, utils, shared infrastructure)
config/         # Django settings, URLs, ASGI/WSGI
docs/           # Documentation
tests/          # Test suite
```

## Quick Start

### Prerequisites

- Python 3.14+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (package manager)

### Setup

```bash
# Start infrastructure (PostgreSQL + Redis)
docker compose up -d

# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Start development server
uv run python manage.py runserver
```

## Code Quality

```bash
uv run ruff check .     # Lint
uv run ruff format .    # Format
uv run mypy .           # Type check
uv run pytest           # Tests
```

## Continuous Integration (CI)

GitHub Actions runs lint, type check, and tests on every push to `main` and PR targeting `main`. See [docs/ci.md](docs/ci.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Development Guide](docs/development.md)
- [Continuous Integration](docs/ci.md)
