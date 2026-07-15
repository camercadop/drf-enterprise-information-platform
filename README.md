# DRF Enterprise Information Platform

[![CI](https://github.com/camercadop/drf-enterprise-information-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/camercadop/drf-enterprise-information-platform/actions/workflows/ci.yml)

Multi-tenant enterprise platform built with Django REST Framework. Designed as a modular monolith with convention-over-configuration defaults, a plugin-based extensibility model, and security by default.

## Why This Exists

Enterprise applications share recurring infrastructure challenges: tenant isolation, consistent API contracts, audit trails, and authentication that scales across organizations. Building these from scratch for each project leads to inconsistent implementations, security gaps, and duplicated effort.

This platform solves these problems once — so domain teams can focus on business logic instead of reinventing infrastructure.

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
apps/           # Domain modules (iam_auth, iam_roles, iam_users, tenants)
core/           # Framework foundations (base classes, utils, shared infrastructure)
config/         # Django settings, URLs, ASGI/WSGI
docs/           # Documentation
tests/          # Test suite
```

## Architecture Overview

```mermaid
graph TD
    Client[API Client] --> Views

    subgraph apps["apps/ — Domain Modules"]
        Views[Views / ViewSets]
        Serializers[Serializers]
        Models[Models]
    end

    subgraph core["core/ — Framework Foundations"]
        BaseViews[Base Views]
        BaseSerializers[Base Serializers + Plugins]
        BaseModels[Base Models]
        Permissions[Permissions]
        Renderer[API Renderer]
    end

    Views --> BaseViews
    Serializers --> BaseSerializers
    Models --> BaseModels
    Views --> Permissions
    Views --> Renderer

    BaseModels --> PostgreSQL[(PostgreSQL)]
    BaseViews --> Redis[(Redis)]
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

- [Vision](docs/vision.md)
- [Architecture](docs/architecture.md)
- [API Conventions](docs/api-conventions.md)
- [Error Codes](docs/error-codes.md)
- [Security](docs/security.md)
- [Code Style](docs/code-style.md)
- [Data Model](docs/data-model.md)
- [Development Guide](docs/development.md)
- [Deployment](docs/deployment.md)
- [Testing](docs/testing.md)
- [Continuous Integration](docs/ci.md)
- [Architecture Decision Records](docs/adr/README.md)
- [Development Guidelines](docs/guidelines/README.md)

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
