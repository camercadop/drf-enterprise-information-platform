# Data Model

This document describes the platform's data model organized by domain. Each section includes the schema, relationships, constraints, and design notes.

## Overview

```mermaid
erDiagram
    Tenant ||--o{ TenantMembership : "has"
    User ||--o{ TenantMembership : "belongs via"
    User ||--o{ UserPasswordHistory : "tracks"
```

---

## Base Layer

All models inherit from a composable abstract hierarchy:

```
TimeStampedModel (abstract)
    ├── created_at
    └── updated_at

SoftDeletableModel (abstract)
    ├── deleted_at
    └── deleted_by

CoreModel (abstract) ← TimeStampedModel + SoftDeletableModel
    └── id (UUID, PK)

BaseModel (abstract) ← CoreModel
    └── tenant (FK → Tenant)
```

Apps inherit from the appropriate level:
- `CoreModel` — platform-level entities (no tenant scope)
- `BaseModel` — tenant-scoped domain entities

---

## Tenants

```mermaid
erDiagram
    Tenant {
        UUID id PK
        VARCHAR name
        VARCHAR code UK
        BOOLEAN is_active
        JSON config
        DATETIME created_at
        DATETIME updated_at
    }
```

| Field | Purpose |
|-------|---------|
| code | Unique internal identifier for programmatic reference |
| config | Flexible key-value store for tenant-specific settings (password policies, feature flags, etc.) |

---

## Users

```mermaid
erDiagram
    User {
        UUID id PK
        VARCHAR email UK
        VARCHAR first_name
        VARCHAR last_name
        VARCHAR password
        BOOLEAN is_active
        BOOLEAN is_superuser
        DATETIME created_at
        DATETIME updated_at
    }

    UserProfile {
        UUID id PK
        UUID user_id FK
        JSON personal_info
    }

    TenantRole {
        UUID id PK
        UUID tenant_id FK
        VARCHAR name
        TEXT description
        DATETIME created_at
    }

    TenantMembership {
        UUID id PK
        UUID user_id FK
        UUID tenant_id FK
        UUID role_id FK
        BOOLEAN is_admin
        BOOLEAN is_active
        DATETIME joined_at
    }

    User ||--o| UserProfile : "has one"
    User ||--o{ TenantMembership : "has many"
    Tenant ||--o{ TenantMembership : "has many"
    Tenant ||--o{ TenantRole : "has many"
    TenantRole ||--o{ TenantMembership : "assigned via"
```

**Constraints:**

| Model | Constraint | Fields |
|-------|-----------|--------|
| TenantRole | unique_role_per_tenant | (tenant, name) |
| TenantMembership | unique_user_tenant | (user, tenant) |

**Design decisions:**
- `User` exists at the platform level — not scoped to any tenant. A user can belong to multiple tenants.
- Tenant association is modeled through `TenantMembership`, which assigns exactly one `TenantRole` per membership.
- `UserProfile` separates mutable personal data from the auth-critical `User` table.
- `TenantRole` is defined per tenant — each tenant manages its own role definitions independently.
- `is_admin` on `TenantMembership` provides a fast-path check without querying the role's permissions.

---

## Authentication

```mermaid
erDiagram
    UserPasswordHistory {
        UUID id PK
        UUID user_id FK
        VARCHAR hashed_password
        DATETIME created_at
    }

    User ||--o{ UserPasswordHistory : "has many"
```

**Design decisions:**
- Stores the hashed password (never plaintext) each time a user changes their password.
- On password change, the current hash is saved to history before the new password is set.
- Validation rejects any new password that matches the last 5 entries (configurable via `PASSWORD_HISTORY_LIMIT`).
