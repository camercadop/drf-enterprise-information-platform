# sys_audit

System audit trail — append-only record of all state-changing operations.

## Purpose

Implements ADR-009 (Auditability by Design). Every create, update, and delete operation produces an immutable audit record identifying the actor, action, target resource, tenant boundary, and timestamp.

## How It Works

```mermaid
graph LR
    Op[State-changing operation] --> Plugin[AuditPlugin]
    Plugin --> Helper[log_audit]
    Helper --> DB[(sys_audit_log table)]
```

- **AuditPlugin** — a `SerializerPlugin` registered globally in `SERIALIZER_PLUGINS`. Hooks into `on_post_create`, `on_post_update`, and `on_post_destroy` lifecycle boundaries.
- **log_audit()** — helper function in `services.py`. Single entry point for writing audit records. Used by the plugin and available for direct use in background tasks or management commands.

## Model: AuditLog

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `actor` | FK (User) | Who performed the action |
| `action` | CharField (free-form) | Operation name (e.g., `create`, `update`, `delete`, `login`, `password_change`, `state_change`) |
| `target_type` | CharField | Model label (e.g., `tenants.team`) |
| `target_id` | UUID | PK of the affected resource |
| `tenant_id` | UUID (nullable) | Tenant boundary context |
| `changes` | JSONField | Full payload (create), field diff (update), empty (delete) |
| `created_at` | DateTimeField | When the operation was recorded |

## Append-Only Enforcement

- `AuditLog.save()` raises `NotImplementedError` on update attempts
- `AuditLog.delete()` raises `NotImplementedError`
- `AuditLogManager` blocks `update()` and `delete()` at the queryset level

## Usage

### Automatic (via plugin)

All CRUD operations through `BaseSerializer` and `BaseViewSet` are automatically audited. No action required.

### Manual (via helper)

For non-CRUD operations (login, password change, state transitions, etc.), call `log_audit()` directly from the view or service:

```python
from apps.sys_audit.services import log_audit

# CRUD example
log_audit(
    actor=user,
    action="create",
    target_type="tenants.team",
    target_id=team.pk,
    tenant_id=tenant.pk,
    changes={"name": "Engineering"},
)

# Non-CRUD example
log_audit(
    actor=user,
    action="password_change",
    target_type="users.user",
    target_id=user.pk,
    tenant_id=tenant.pk,
)
```

## Scope

This module records **state-changing operations** for compliance and incident investigation. It does not cover user activity tracking (page visits, exports, etc.) — that belongs in a separate system module (see open question #5 in `_SCRATCH_DECISIONS.md`).
