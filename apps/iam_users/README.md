# IAM Users

Platform-level user identity, profiles, and tenant membership.

## Relationships

```mermaid
erDiagram
    User ||--o| UserProfile : "has one"
    User ||--o{ TenantMembership : "has many"
    Tenant ||--o{ TenantMembership : "has many"
    TenantRole ||--o{ TenantMembership : "assigned via"
```

## Models

### User

Authentication identity. Uses email as login credential. Platform-level (not scoped to any tenant). Inherits from `AbstractBaseUser` and `PermissionsMixin`.

### UserProfile

One-to-one extension for non-auth personal data (phone, avatar, bio). Separated from `User` to reduce migration churn on the auth table.

### TenantMembership

Links a user to a tenant with exactly one role (from `iam_roles.TenantRole`). `is_admin` provides a fast-path privilege check without querying role permissions. Deleting a role with active memberships is blocked (`PROTECT`).

## Design Decisions

- A user can belong to multiple tenants via separate memberships.
- `User`, `UserProfile`, and `TenantMembership` use hard-delete.
