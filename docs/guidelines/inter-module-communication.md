# Inter-Module Communication

How domain modules (`apps/`) interact with each other — allowed interfaces, forbidden patterns, and dependency direction.

---

## Overview

Each app in `apps/` is a self-contained domain module. Modules must communicate through explicit, narrow interfaces rather than reaching into each other's internals. This keeps modules independently evolvable and makes future service extraction possible.

```mermaid
flowchart LR
    A[apps/iam_auth] --> B[apps/tenants]
    A --> C[apps/iam_users]
    D[apps/future_module] --> B
    D --> C
    B -.->|NEVER| A
    C -.->|NEVER| A
```

Arrows represent allowed dependency direction. Dotted lines represent forbidden dependencies.

---

## Dependency Direction

### Rules

1. `core/` depends on nothing (foundation layer)
2. Any app can depend on `core/`
3. Any app can depend on `apps/tenants`, `apps/iam_users`, and `apps/iam_roles` (shared domain models)
4. `apps/tenants`, `apps/iam_users`, and `apps/iam_roles` must not depend on downstream apps
5. `apps/iam_auth` can depend on `apps/tenants` and `apps/iam_users` (it orchestrates login)
6. No app may depend on `apps/iam_auth` (auth is a leaf consumer, not a provider)

### Dependency Matrix

| Module | Can depend on |
|--------|---------------|
| `core/` | Nothing |
| `apps/tenants` | `core/` |
| `apps/iam_users` | `core/`, `apps/tenants`, `apps/iam_roles` |
| `apps/iam_roles` | `core/`, `apps/tenants` |
| `apps/iam_auth` | `core/`, `apps/tenants`, `apps/iam_users` |
| Any new app | `core/`, `apps/tenants`, `apps/iam_users`, `apps/iam_roles` |

---

## Allowed Interfaces

When module A needs data or behavior from module B, use these patterns (in order of preference):

### 1. Foreign Key by UUID

Reference another module's model via UUID FK. This is the standard approach for relational data:

```python
from apps.iam_users.models import User

class Document(TenantAwareModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
```

### 2. Public Utility Functions

The owning module exposes a function that returns plain data (dicts, dataclasses, or primitives) — not model instances:

```python
# apps/tenants/utils.py (public interface)
def get_tenant_setting(tenant_id: uuid.UUID, key: str) -> str | None:
    """Retrieve a single tenant setting value by key."""
    ...
```

```python
# apps/documents/views.py (consumer)
from apps.tenants.utils import get_tenant_setting

max_size = get_tenant_setting(tenant_id, "max_upload_size_mb")
```

### 3. Model Imports for Read-Only Queries

When you need to filter or join against another module's model in a queryset, import the model directly. This is acceptable for read-only access:

```python
from apps.iam_users.models import User

users = User.objects.filter(is_active=True)
```

Do not call `.save()`, `.delete()`, or mutate instances from another module's model.

### 4. Domain Events via the Event Bus

When module A needs to notify other modules that something happened — without knowing who is listening — publish a domain event via `sys_eventbus`:

```python
# apps/dms_ingestion/tasks.py (producer — non-request context)
from apps.sys_eventbus.publisher import publish

publish(
    event_type="document.created",
    payload={"document_id": str(document.pk)},
    tenant_id=str(tenant_id),
    actor_id=str(actor_id),
)
```

```python
# apps/dms_ingestion/views.py (producer — request context)
from apps.sys_eventbus.publisher import publish_event_from_request

publish_event_from_request(
    event_type="document.created",
    payload={"document_id": str(document.pk)},
    request=request,
)
```

```python
# apps/dms_documents/event_handlers.py (consumer)
from apps.sys_eventbus.registry import event_handler
from apps.sys_eventbus.envelope import EventEnvelope


@event_handler("document.created")
def on_document_created(envelope: EventEnvelope) -> None:
    """React to a document.created event."""
    ...
```

Use this pattern when:
- The producer should not know about the consumer
- Multiple modules may react to the same event
- The reaction can be deferred (async, non-blocking)

Do not use events as a substitute for synchronous service calls when the producer needs a result or must guarantee the consumer ran before continuing.

---

## Forbidden Patterns

| Pattern | Why It's Forbidden |
|---------|-------------------|
| Importing serializers from another app | Serializers encode API-layer concerns; coupling to them creates brittle dependencies |
| Importing views from another app | Views are entry points, not reusable components |
| Calling `.save()` or `.delete()` on another app's model instances | Mutations must go through the owning module's interface to preserve invariants |
| Importing from another app's `migrations/` | Migrations are internal implementation details |
| Circular dependencies between apps | If A depends on B and B depends on A, extract the shared concern into `core/` or a new app |

---

## Mutations Across Boundaries

When module A needs to *change* data owned by module B:

1. B exposes a public function (service function) that performs the mutation and enforces its own invariants
2. A calls that function — never manipulates B's models directly

```python
# apps/tenants/services.py (owner exposes mutation)
def deactivate_membership(membership_id: uuid.UUID, actor: User) -> None:
    """Deactivate a membership. Enforces state preconditions."""
    ...
```

```python
# apps/some_other_app/views.py (consumer)
from apps.tenants.services import deactivate_membership

deactivate_membership(membership_id=pk, actor=request.user)
```

---

## Future Evolution

These module boundaries map directly to service extraction:

- Each app's public interface (utility functions, service functions) becomes the service's API contract
- FK references become cross-service ID references (resolved via API calls or events)
- The dependency direction determines extraction order — leaf modules (no dependents) extract first

---

## Decision Guide

| Scenario | Approach |
|----------|----------|
| Need to reference another module's entity | FK by UUID |
| Need to read a setting or computed value from another module | Public utility function in the owning module |
| Need to filter/join against another module's model | Import the model, read-only queries only |
| Need to mutate another module's data | Call a service function exposed by the owning module |
| Need to notify other modules that something happened (async, no result needed) | Publish a domain event via `sys_eventbus.publisher.publish()` |
| Shared logic needed by multiple apps | Put it in `core/` (if domain-agnostic) or extract a new shared app |
| Two apps depend on each other | Refactor — extract shared concern into `core/` or a third app |
