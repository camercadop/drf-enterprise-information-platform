# sys_user_event

User event tracking and authentication attempt logging.

## Purpose

Records two categories of observability data:

- **UserEvent** — behavioral events emitted by authenticated users (login, logout, password change, membership transitions)
- **AuthAttemptLog** — every login attempt regardless of outcome, for security monitoring and brute-force forensics

This module is distinct from `sys_audit`, which records state-changing resource operations with immutability guarantees. User events and auth attempts are behavioral/security records with different retention needs and no immutability contract.

## Models

### UserEvent (`sys_user_events`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `actor` | FK (User, SET_NULL) | User who triggered the event; nullable to survive deletion |
| `user_email` | EmailField | Denormalized email for identity reference after actor deletion |
| `category` | CharField | Logical grouping (e.g., `auth`, `membership`) |
| `event` | CharField | Specific event name (e.g., `login`, `logout`) |
| `tenant` | FK (Tenant, nullable) | Tenant boundary context |
| `metadata` | JSONField | Event-specific payload |
| `created_at` | DateTimeField | When the event was recorded |

### AuthAttemptLog (`sys_auth_attempts`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `email` | EmailField | Email submitted in the attempt |
| `ip_address` | CharField | Requester IP (IPv4 or IPv6) |
| `success` | BooleanField | Whether authentication succeeded |
| `failure_reason` | CharField | Machine-readable failure code (empty on success) |
| `tenant` | FK (Tenant, nullable) | Resolved tenant context at attempt time |
| `created_at` | DateTimeField | When the attempt was recorded |

## API Endpoints

| Method | URL | Permission |
|--------|-----|------------|
| GET | `api/sys/user-events/` | Superuser or tenant admin |
| GET | `api/sys/auth-attempts/` | Superuser or tenant admin |

Superusers see all records. Tenant admins see only records scoped to their tenant.

### Filters

`UserEvent`: `category`, `event`, `actor`, `tenant_id`, `created_at` (supports `__gte`, `__lte`, `__gt`, `__lt`, `__icontains`, `__in`, `__isnull`)

`AuthAttemptLog`: `email`, `ip_address`, `success`, `tenant_id`, `created_at` (supports same suffixes)

## Usage

```python
from apps.sys_user_event.services import record_event

record_event(
    actor=request.user,
    user_email=request.user.email,
    category="auth",
    event="login",
    metadata={"ip_address": "1.2.3.4"},
)
```
