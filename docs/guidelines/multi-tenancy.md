# Multi-Tenancy

How to implement tenant-scoped resources — from model inheritance and automatic query filtering to server-side tenant injection on writes and per-tenant runtime settings.

---

## Overview

Strategy: **shared database with tenant FK filtering, isolation at the permission layer.**

A single database holds all tenants' data. Isolation is enforced at runtime through:

1. A `tenant` FK on every tenant-scoped model
2. Automatic query filtering via `TenantFilterBackend`
3. Server-side tenant injection via `TenantInjectionSerializerPlugin`
4. Tenant context carried in JWT claims

---

## Tenant Context Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant JWT
    participant Filter as TenantFilterBackend
    participant Plugin as TenantInjectionPlugin

    Client->>API: POST /api/auth/login/ {email, password, tenant_id?}
    API->>API: Resolve membership
    API->>JWT: Encode tenant_id in claims
    API-->>Client: {access, refresh}

    Client->>API: GET /api/invoices/ (Bearer token)
    API->>JWT: Decode → extract tenant_id
    JWT-->>Filter: tenant_id
    Filter->>Filter: queryset.filter(tenant_id=...)
    API-->>Client: Scoped results

    Client->>API: POST /api/invoices/ (Bearer token)
    API->>JWT: Decode → extract tenant_id
    JWT-->>Plugin: tenant_id
    Plugin->>Plugin: validated_data["tenant_id"] = tenant_id
    API-->>Client: Created resource
```

### Extracting Tenant Context

Use `apps.tenants.utils.get_tenant_id(request)` to read the tenant from the JWT:

```python
from apps.tenants.utils import get_tenant_id

tenant_id = get_tenant_id(request)  # str | None
```

---

## Model Layer

```mermaid
classDiagram
    class TimeStampedModel {
        <<abstract>>
        +created_at
        +updated_at
    }
    class SoftDeletableModel {
        <<abstract>>
        +deleted_at
        +deleted_by
        +delete()
        +hard_delete()
    }
    class BaseModel {
        <<abstract>>
        +UUID id
    }
    class TenantAwareModel {
        <<abstract>>
        +FK tenant
    }

    TimeStampedModel <|-- BaseModel
    SoftDeletableModel <|-- BaseModel
    BaseModel <|-- TenantAwareModel

    note for BaseModel "Platform-level entities\n(no tenant scope)"
    note for TenantAwareModel "Tenant-scoped entities"
```

### Tenant-Scoped Models

Inherit from `TenantAwareModel` — includes UUID pk, timestamps, soft-delete, and a `tenant` FK:

```python
from apps.tenants.models import TenantAwareModel

class Invoice(TenantAwareModel):
    number = models.CharField(max_length=50)

    class Meta:
        abstract = False
        db_table = "invoices"
```

### Platform-Level Models

Inherit from `BaseModel` — same as `TenantAwareModel` but without the tenant FK:

```python
from core.base.models import BaseModel

class Tenant(BaseModel):
    name = models.CharField(max_length=255)
```

### Decision Rule

| The resource belongs to a tenant | Use |
|----------------------------------|-----|
| Yes | `TenantAwareModel` |
| No (platform-wide) | `BaseModel` |

---

## Query Filtering

`TenantFilterBackend` is registered globally and automatically scopes querysets.

```mermaid
flowchart TD
    A[Incoming request] --> B{Model has tenant_id?}
    B -- No --> C[No-op: return full queryset]
    B -- Yes --> D{view.tenant_scoping = False?}
    D -- Yes --> C
    D -- No --> E{JWT has tenant_id claim?}
    E -- No --> F[Return empty queryset]
    E -- Yes --> G[Filter queryset by tenant_id]
```

- If the model has a `tenant_id` field → filters by the JWT's `tenant_id`
- If no `tenant_id` claim is present → returns an empty queryset (deny by default, per ADR-004)
- If the model has no `tenant_id` field → no-op

### Opting Out

Set `tenant_scoping = False` on the viewset for platform-level resources:

```python
class TenantViewSet(BaseViewSet):
    tenant_scoping = False  # No automatic tenant filtering
```

### Conditional Scoping

Use a property for dynamic behavior (e.g., superusers see all):

```python
class TeamViewSet(BaseViewSet):
    @property
    def tenant_scoping(self) -> bool:
        if self.request.user.is_superuser:
            return False
        return True
```

---

## Write Operations

`TenantInjectionSerializerPlugin` (registered globally in settings) handles tenant assignment:

```mermaid
flowchart TD
    subgraph Create
        A1[on_pre_create] --> B1{Model has tenant_id?}
        B1 -- No --> C1[No-op]
        B1 -- Yes --> D1{JWT has tenant_id?}
        D1 -- No --> E1[Raise PermissionDeniedError]
        D1 -- Yes --> F1[Inject tenant_id into validated_data]
    end

    subgraph Update
        A2[on_pre_update] --> B2{Model has tenant_id?}
        B2 -- No --> C2[No-op]
        B2 -- Yes --> D2{tenant_id in validated_data?}
        D2 -- No --> C2
        D2 -- Yes --> E2{Matches current tenant?}
        E2 -- Yes --> F2[Strip tenant_id from data]
        E2 -- No --> G2[Raise PermissionDeniedError]
    end
```

### On Create

- Injects `tenant_id` from the JWT into `validated_data`
- Raises `PermissionDeniedError` if the model requires a tenant but no claim is present
- The client never sends `tenant_id` — it's always derived server-side

### On Update

- Strips `tenant_id` from `validated_data` if it matches the current value
- Raises `PermissionDeniedError` if the client attempts to reassign to a different tenant

### Self-Guarding

The plugin checks `hasattr(model, "tenant_id")` and no-ops for models without a tenant FK. No exclusion needed for platform-level serializers.

---

## Superuser Bypass

- `TenantFilterBackend`: bypassed when `tenant_scoping = False` (set explicitly or via property)
- `BasePermission.check_tenant_ownership`: superusers skip tenant membership checks
- `TenantInjectionSerializerPlugin`: still requires a tenant context — superusers must select a tenant when creating tenant-scoped resources

---

## Adding a New Tenant-Scoped Resource (Checklist)

1. **Model** — inherit from `TenantAwareModel`
2. **Serializer** — inherit from `BaseSerializer` or `DefaultModelSerializer`; exclude `tenant` from writable fields (the plugin handles it)
3. **ViewSet** — inherit from `BaseViewSet`; leave `tenant_scoping = True` (default)
4. **URLs** — register with the app's router
5. **No extra wiring needed** — the global plugin and filter backend handle isolation automatically

```python
# serializers.py
class InvoiceSerializer(DefaultModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "number", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

# views.py
class InvoiceViewSet(BaseViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
```

---

## Tenant Settings

Behavioral configuration is stored in `TenantSetting` (key-value per tenant):

```python
from apps.tenants.utils import get_tenant_setting, get_tenant_settings

# Single setting
limit = get_tenant_setting(tenant_id, "password_min_length", default="8")

# All settings with a prefix
flags = get_tenant_settings(tenant_id, prefix="feature_flag_")
```

Use tenant settings for runtime-configurable behavior (password policies, feature flags, rate limits) — not for static metadata (that goes in `Tenant.details`).

---

## Common Pitfalls

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Including `tenant` or `tenant_id` as a writable serializer field | Client can forge tenant ownership | Omit it from `fields` — the plugin injects it server-side |
| Manually filtering by tenant in `get_queryset` | Double-filtering, or inconsistent behavior if the backend changes | Rely on `TenantFilterBackend`; only override for additional filters |
| Writing tests without tenant context in the JWT | `TenantFilterBackend` returns an empty queryset, tests fail silently | Use the test helpers that build tokens with `tenant_id` claim |
| Setting `tenant_scoping = False` to "fix" empty querysets | Disables isolation for all users | Investigate missing tenant claim instead; use the property pattern for conditional bypass |
| Passing `tenant_id` from the client on create | Plugin ignores client-sent values but it adds noise and confuses API consumers | Document that `tenant_id` is never accepted in request bodies |
| Storing per-tenant config in model fields on `Tenant` | Schema changes for every new setting | Use `TenantSetting` for runtime-configurable values |

---

## Decision Guide

| Scenario | Approach |
|----------|----------|
| Resource belongs to a single tenant | Inherit from `TenantAwareModel`; leave `tenant_scoping = True` (default) |
| Platform-level resource (no tenant) | Inherit from `BaseModel`; set `tenant_scoping = False` on viewset |
| Superuser needs cross-tenant read access | Use `tenant_scoping` as a property that returns `False` for superusers |
| Superuser creates a tenant-scoped resource | Superuser must select a tenant context — plugin still requires a claim |
| Endpoint is public (no auth) | Use `BaseModel` or set `tenant_scoping = False`; no JWT means no tenant claim |
| Need per-tenant runtime configuration | Use `TenantSetting` via `get_tenant_setting()` |
| Need to filter by additional fields beyond tenant | Override `get_queryset` for the extra filter; tenant filtering is still automatic |
| Migrating an existing model to tenant-scoped | Add `tenant` FK, inherit from `TenantAwareModel`, backfill existing rows, remove `tenant_scoping = False` |
