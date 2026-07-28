# DRF Enterprise Information Platform

[![CI](https://github.com/camercadop/drf-enterprise-information-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/camercadop/drf-enterprise-information-platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.14-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-6-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)

Multi-tenant enterprise platform built with Django REST Framework. Provides tenant isolation, audit trails, JWT authentication, and role-based access control out of the box. Designed as a modular monolith with convention-over-configuration defaults, a plugin-based extensibility model, and security-first design — so domain teams can focus on business logic instead of reinventing infrastructure.

[Read the full vision and strategy](docs/vision.md)

## Why This Exists

Enterprise applications share recurring infrastructure challenges: tenant isolation, consistent API contracts, audit trails, and authentication that scales across organizations. Building these from scratch for each project leads to inconsistent implementations, security gaps, and duplicated effort.

This platform solves these problems once — so domain teams can focus on business logic instead of reinventing infrastructure.

## Target Audience

- Development teams building internal enterprise tools, B2B SaaS backends, or multi-organization platforms
- Platform engineers who need a well-structured backend with clear extension points
- System integrators connecting enterprise systems through a unified API layer
- SaaS developers who need multi-tenant infrastructure without building it from scratch
- Organizations that require tenant-scoped data, role-based access, and audit trails without building custom infrastructure

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.14 |
| Framework | Django 6 + Django REST Framework |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Async Processing | Celery (broker: Redis) |
| Auth | JWT (simplejwt) with token blacklisting |
| Observability | OpenTelemetry, Prometheus, Grafana |
| Containers | Docker + Docker Compose |
| Quality | Ruff, mypy, pre-commit |
| Testing | Pytest, Factory Boy |
| CI | GitHub Actions |

## Key Features

### Data

- **Multi-tenancy** — shared database with tenant FK filtering, isolation at the permission layer
- **Soft-delete** — default deletion strategy with `deleted_at`/`deleted_by` fields
- **Audit trail** — automatic write-operation logging via `sys_audit` plugin
- **Tenant settings** — per-tenant configuration catalog with schema validation
- **Event bus** — Redis-based domain event publishing with retry and dead-letter queue

### Architecture

- **Plugin system** — stateless plugins for cross-cutting concerns on serializers
- **Template methods** — `pre_*/do_*/post_*` hooks for per-class customization
- **Permission catalog** — declarative, JSON-based permission declarations synced via management command

### API & Auth

- **Standard API envelope** — consistent `{status, data}` response format
- **JWT authentication** — short-lived access tokens, rotating refresh tokens, tenant context in claims
- **MFA** — TOTP-based multi-factor authentication with backup codes and per-tenant enforcement
- **IP filtering & lockout** — per-tenant IP allowlisting and brute-force lockout
- **Idempotency** — Redis-backed idempotency middleware for mutating requests
- **Health check** — unauthenticated endpoint for infrastructure monitoring

## Extended Capabilities

Beyond core functionality, the platform includes comprehensive enterprise features:

- **Identity Management** — Teams, MFA (TOTP), authentication auditing, user events
- **Document Management** — Upload, versioning, metadata, categories, ingestion pipeline
- **API Management** — Versioning, rate limiting, OpenAPI docs
- **Event Platform** — Domain events, Redis-based event bus, retry, dead-letter queue
- **Background Processing** — Celery tasks with Redis broker
- **Observability** — OpenTelemetry tracing and metrics, Prometheus, Grafana dashboards
- **Audit & Governance** — Comprehensive audit logs, soft delete, tenant settings
- **Notifications** — Email, webhooks (roadmap)
- **Search Extensions** — Filters, ordering; full-text search (roadmap)

## Platform Roadmap

The platform evolves through structured phases:

- **Phase 1 — Foundation** — Core architecture, authentication, users, documents
- **Phase 2 — Enterprise Features** — Document lifecycle, advanced search, security
- **Phase 3 — Enterprise Platform** — Integrations, operations, observability

[View detailed roadmap](ROADMAP.md)

## Project Structure

```
apps/               # Domain modules
core/               # Framework foundations (base classes, utils, shared infrastructure)
config/             # Django settings, URLs, ASGI/WSGI
infra/              # OTel Collector, Prometheus, and Grafana provisioning configs
docs/               # Documentation
tests/              # Test suite
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

## Branching Strategy

- `main` — production-ready code, only receives merges from `dev`
- `dev` — active development, all feature/fix branches target `dev`

## Continuous Integration (CI)

GitHub Actions runs on every push to `main`/`dev` and PRs targeting either branch. Steps include lint, type check, permission catalog validation, OpenAPI schema validation, migrations, and tests. See [docs/ci.md](docs/ci.md).

## Documentation

- [Vision](docs/vision.md)
- [Architecture](docs/architecture.md)
- [C4 Context Diagram](docs/c4-context.md)
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
- [Platform Roadmap](ROADMAP.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching conventions, commit message format, PR guidelines, and how to add a new domain module.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
