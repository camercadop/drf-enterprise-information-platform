# Architecture

## Design Principles

- **API First** — the REST API is the primary interface
- **Modular Monolith** — independent domain modules, evolvable to microservices
- **Convention over Configuration** — base classes provide sensible defaults
- **Security by Default** — authentication required, tenant isolation enforced
- **Extensibility** — plugin system and template methods for customization without modification

## Layers

```
┌─────────────────────────────────────────┐
│  apps/                                  │  Domain modules
│  (identity, tenants, documents, etc.)   │
├─────────────────────────────────────────┤
│  core/                                  │  Framework foundations
│  (base classes, utils, shared infra)    │
├─────────────────────────────────────────┤
│  config/                                │  Django configuration
│  (settings, urls, wsgi/asgi)            │
└─────────────────────────────────────────┘
```

### core/ — Framework Foundations

Provides base classes that all domain modules inherit from. This layer defines:

- **Base models** — `TimeStampedModel`, `SoftDeletableModel`, `BaseModel`
- **Base serializers** — `BaseSerializer` with plugin system and template method lifecycle
- **Base views** — `BaseViewSet` with filtering, ordering, permissions
- **Exceptions** — Centralized exception hierarchy
- **Permissions** — Tenant-aware permission classes
- **Pagination** — Configurable pagination strategies
- **Filters** — Base filter classes with common fields

### apps/ — Domain Modules

Each module is a self-contained Django app with its own models, serializers, views, and URLs. Modules communicate through well-defined interfaces (not direct imports between apps).

## Multi-Tenancy

Strategy: shared database with tenant FK filtering.

- Every resource belongs to a `Tenant`
- Queries are filtered by the authenticated user's tenant
- Isolation enforced at the permission layer
- Cross-tenant access possible for platform admins

## Soft-Delete

Default deletion strategy across the platform:

- `BaseModel` includes `deleted_at` and `deleted_by` fields
- `model.delete()` performs soft-delete (sets `deleted_at`)
- `model.hard_delete()` performs actual deletion
- Querysets exclude soft-deleted records by default
- `SoftDeletablePlugin` handles representation in API responses

## Extensibility Model

Two complementary patterns for extending behavior:

- **Plugins** — stateless classes for cross-cutting concerns (horizontal)
- **Template methods** — overridable hooks for per-class customization (vertical)

See `docs/guidelines/extensible-lifecycle-design.md` for details.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python |
| Framework | Django + Django REST Framework |
| Database | PostgreSQL |
| Cache | Redis |
| Async | Celery (broker: Redis) |
| Containers | Docker + Docker Compose |
| Quality | Ruff, mypy, pre-commit |
| Testing | Pytest, Factory Boy |
| Docs | OpenAPI / Swagger |
