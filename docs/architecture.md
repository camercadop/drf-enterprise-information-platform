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
- **Middleware** — Platform-level middleware (idempotency)
- **Celery** — Custom `TaskResultBackend` with Postgres UUID primary keys and `async_tasks` schema isolation

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
  - **Serializer plugins** (`DEFAULT_SERIALIZER_PLUGINS`) — participate in create/update/validate lifecycle and field resolution (`filter_fields`)
  - **ViewSet plugins** (`DEFAULT_VIEWSET_PLUGINS`) — participate in context building and destroy lifecycle
- **Template methods** — overridable hooks for per-class customization (vertical)

Both plugin settings live inside the `REST_FRAMEWORK` configuration dict.

## Docker Compose Services

The `docker-compose.yml` defines the following services for local development:

- `postgres` — PostgreSQL 16
- `redis` — Redis 7
- `app` — Django application
- `celery` — Celery worker
- `otel-collector` — OpenTelemetry Collector
- `tempo` — Grafana Tempo (traces)
- `prometheus` — Prometheus (metrics)
- `grafana` — Grafana (dashboards)

## Observability

All dev infra configuration for OpenTelemetry, Prometheus, and Grafana lives under `infra/`. This keeps platform observability assets separate from application code and makes the infrastructure reusable across environments.

| Directory | Purpose |
|-----------|---------|
| `infra/otel-collector-config.yaml` | OTel Collector pipelines and exporters |
| `infra/prometheus.yml` | Prometheus scrape configuration |
| `infra/grafana/provisioning/` | Datasource and dashboard provisioning for Grafana |

## Dependency Injection

Runtime dependencies (plugins, storage backends, pipeline processors) are resolved from dotted-path strings in settings via `core.module_resolver`:

- `resolve(dotted_path)` — imports and returns the object at the path
- `resolve_instance(dotted_path)` — imports and instantiates with no arguments

Swap any dependency by changing its dotted path in settings — no call sites change. All plugin systems, storage backends, and pipeline processors use these helpers as the single resolution mechanism.


## Background Processing

Celery is used for asynchronous task execution with Redis as the broker.

- Broker: Redis (database 1, separate from the cache on database 0)
- Result backend: PostgreSQL via SQLAlchemy, stored in the `async_tasks` schema
- Task results use Postgres-generated UUID primary keys (`gen_random_uuid()`)
- Results include a `created_at` timestamp set by the database at insert time
- In tests, `CELERY_TASK_ALWAYS_EAGER = True` runs tasks synchronously — no worker required

The custom backend lives in `core/celery/backend.py` and is wired in `config/celery.py`.

## Event Bus

`apps/sys_eventbus` provides platform-wide publish/subscribe infrastructure for domain events.

- Transport: Redis Streams (`sys:eventbus`) — messages persist, consumer groups supported
- Consumer: Celery beat task (`poll_eventbus`) polls the stream on a configurable interval
- Dispatch: each handler is executed as an independent Celery task (`dispatch_handler`)
- Delivery guarantee: at-most-once — messages are acknowledged before handler execution
- Idempotency: `ProcessedEvent` table prevents double-execution across retries
- Dead letter: messages that exhaust retries are written to `DeadLetterEvent` for operator inspection
- Handler registration: `@event_handler("event.type")` decorator in each app's `event_handlers.py`, auto-discovered at startup

See [sys_eventbus README](../apps/sys_eventbus/README.md) for the full public API and usage.

## Business Logic Layer

Business logic lives primarily in models, serializers (via the lifecycle hooks and plugin system), and views. A `services.py` module is introduced per app when logic is too complex for a serializer hook or needs to be called from multiple entry points (e.g., views, tasks, signals). There is no platform-wide service layer — the decision is per-domain.

## Authentication

Strategy: JWT with token blacklisting via `djangorestframework-simplejwt`.

- Access tokens are short-lived (30 min), refresh tokens last 7 days
- Refresh tokens rotate on use — the old one is blacklisted automatically
- Login resolves tenant context — `tenant_id` is stored in JWT claims
- Logout blacklists the refresh token server-side
- Password changes enforce complexity rules (tenant-configurable) and prevent reuse of the last 5 passwords
- "Logout all" invalidates every outstanding refresh token for the user

The platform also includes an OAuth2 authorization server (`apps/iam_oauth`) supporting Authorization Code, Client Credentials, and Refresh Token grant types. OAuth2 tokens are JWTs with the same claims format. `TenantJWTAuthentication` handles both user tokens and OAuth2 client credentials tokens — the latter carry no user identity and resolve to `AnonymousUser`. See [iam_oauth README](../apps/iam_oauth/README.md).

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
