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

- **Base models** — `UUIDPrimaryKeyModel`, `TimeStampedModel`, `SoftDeletableModel`, `BaseModel`
- **Base serializers** — `BaseSerializer` with plugin system and template method lifecycle
- **Base views** — `BaseViewSet` with filtering, ordering, declarative permissions
- **Exceptions** — Centralized exception hierarchy + custom handler
- **Renderers** — Standard response envelope
- **Permissions** — Tenant-aware permission classes
- **Pagination** — Configurable pagination strategies
- **Filters** — Base filter classes with common fields

### apps/ — Domain Modules

Each module is a self-contained Django app with its own models, serializers, views, and URLs. Modules communicate through well-defined interfaces (not direct imports between apps).

Related domain apps are grouped by a shared name prefix. Currently: `iam_` groups Identity & Access Management apps (users, authentication, roles, teams).

### apps/ — Infrastructure Modules

Apps that provide cross-cutting concerns rather than business domain logic. The `sys_` prefix marks platform-wide infrastructure (audit, health, permissions). Apps scoped to a specific domain area are grouped by that domain name (e.g., `tenant_settings` belongs to the tenant domain).

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

Soft-delete logic is intentionally distributed across layers — each layer owns its own concern:

- **Model** (`SoftDeletableModel`) — deletion behavior and queryset helpers
- **Filter** (`SoftDeleteFilterBackend`) — queryset scoping and `?include_deleted` parameter
- **Serializer** (`SoftDeletableSerializerMixin`) — API representation of deleted state

No consolidation into a single plugin is planned.

## Extensibility Model

Two complementary patterns for extending behavior:

- **Plugins** — stateless classes for cross-cutting concerns (horizontal)
  - **Serializer plugins** (`DEFAULT_SERIALIZER_PLUGINS`) — participate in create/update/validate lifecycle
  - **ViewSet plugins** (`DEFAULT_VIEWSET_PLUGINS`) — participate in context building and destroy lifecycle
- **Template methods** — overridable hooks for per-class customization (vertical)

Both plugin settings live inside the `REST_FRAMEWORK` configuration dict.


## Business Logic Layer

There is no dedicated service layer. Business logic lives in models, serializers (via the lifecycle hooks and plugin system), and views. A service layer may be introduced for specific domains when complexity justifies it.

## Authentication

Strategy: JWT with token blacklisting via `djangorestframework-simplejwt`.

- Access tokens are short-lived (30 min), refresh tokens last 7 days
- Refresh tokens rotate on use — the old one is blacklisted automatically
- Login resolves tenant context — `tenant_id` is stored in JWT claims
- Logout blacklists the refresh token server-side
- Password changes enforce complexity rules (tenant-configurable) and prevent reuse of the last 5 passwords
- "Logout all" invalidates every outstanding refresh token for the user

## API Response Envelope

All responses follow a consistent structure:

```json
// Success
{"status": "OK", "data": { ... }}

// Error
{"status": "ERROR", "code": "<error_code>", "data": { ... }}
```

Implemented via:
- `core.renderers.APIRenderer` — wraps successful responses
- `core.exceptions.handler.exception_handler` — wraps error responses with extracted error code

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
| Docs | OpenAPI / Swagger (drf-spectacular) |
