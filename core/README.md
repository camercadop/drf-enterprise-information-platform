# Core

Framework foundations shared by all domain apps. Provides base classes, utilities, and cross-cutting infrastructure.

## Model Inheritance

```mermaid
classDiagram
    TimeStampedModel <|-- CoreModel
    SoftDeletableModel <|-- CoreModel
    CoreModel <|-- BaseModel

    class TimeStampedModel {
        +created_at
        +updated_at
    }
    class SoftDeletableModel {
        +deleted_at
        +deleted_by
        +delete()
        +hard_delete()
    }
    class CoreModel {
        +id (UUID)
    }
    class BaseModel {
        +tenant (FK)
    }
```

## Serializer Lifecycle

```mermaid
flowchart TD
    A[validate] --> B[plugin: on_pre_validate]
    B --> C[pre_validate]
    C --> D[do_validate]
    D --> E[post_validate]
    E --> F[plugin: on_post_validate]

    G[create] --> H[plugin: on_pre_create]
    H --> I[pre_create]
    I --> J[do_create]
    J --> K[post_create]
    K --> L[plugin: on_post_create]
```

## Modules

### base/

Abstract models, serializers, and views that all apps inherit from.

- `TimeStampedModel` — `created_at`, `updated_at`
- `SoftDeletableModel` — `deleted_at`, `deleted_by`, soft-delete logic
- `CoreModel` — UUID PK + timestamps + soft-delete (platform-level entities)
- `BaseModel` — CoreModel + tenant FK (tenant-scoped entities)
- `BaseSerializer` — plugin system + template method lifecycle (`pre_create`/`do_create`/`post_create`, same for update and validate)
- `BaseViewSet` — filtering, search, ordering, soft-delete filtering, per-action serializer/queryset dispatch

### exceptions/

Centralized exception hierarchy extending DRF's `APIException`:

- `ValidationError` (400)
- `AuthenticationError` (401)
- `PermissionDeniedError` (403)
- `NotFoundError` (404)
- `ThrottlingError` (429)
- `exception_handler` — custom handler that wraps errors in `{status, code, data}`

### renderers/

- `APIRenderer` — wraps successful responses in `{status: "OK", data: ...}`

### filters/

- `BaseFilterSet` — common filters (id, created_at, updated_at)
- `SoftDeleteFilter` — toggle inclusion of soft-deleted records

### pagination/

- `CustomPagination` — enriched response with page metadata (default: 10 per page)
- `StandardResultsSetPagination` — standard response (default: 20 per page)
- `LargeResultsSetPagination` — optimized for large datasets (default: 100 per page)

### permissions/

- `BasePermission` — ownership and tenant ownership checks
- `IsOwnerOrReadOnly` — write access restricted to object owner
- `IsTenantOwner` — access restricted to tenant owners
- `IsTenantAdmin` — access restricted to tenant admins
- `IsTeamMember` — access restricted to team members

### utils/

- `formatting` — datetime formatting helpers
- `request` — client IP extraction, request data parsing
- `security` — password complexity validation, API key generation, data masking
- `tenant` — extract tenant from JWT, query tenant settings
- `validators` — reusable field validators (username, phone, email domain, uniqueness, file size, date range, JSON schema)
