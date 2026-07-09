# Tenants

Top-level organizational unit for the platform. All domain resources are scoped to a tenant.

## Model

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR | Display name |
| code | VARCHAR (unique) | Internal identifier for programmatic reference |
| is_active | BOOLEAN | Whether the tenant is currently active |
| config | JSON | Flexible key-value store for tenant-specific settings |
| created_at | DATETIME | Auto-set on creation |
| updated_at | DATETIME | Auto-set on save |

## Design Decisions

- Tenants are the isolation boundary — all domain data belongs to exactly one tenant.
- `config` allows per-tenant customization (password policies, feature flags, UI preferences) without schema changes.
- Multi-tenancy uses a shared database with FK filtering, not schema-per-tenant.
