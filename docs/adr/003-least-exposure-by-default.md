# ADR-003: Least Exposure by Default

## Status

Accepted

## Context

The platform handles multi-tenant enterprise data. A single misconfiguration — an unprotected endpoint, a missing tenant check, or an exposed soft-deleted record — can lead to unauthorized access or data leakage.

Relying on developers to explicitly secure each endpoint, filter each query, and hide each sensitive field is error-prone. The secure path must be the default path.

Constraints:

- Enterprise product — data breaches have legal and reputational consequences.
- Multi-tenant — one tenant must never see another tenant's data by accident.
- Growing codebase — new endpoints and fields are added frequently; each is a potential exposure point.

Architectural goals affected: security, data integrity, trust.

## Decision

The platform defaults to the most restrictive access and visibility posture. Access, visibility, and exposure require explicit opt-in. The unsafe path is never the default.

This applies across all layers:

- Authentication — all endpoints require authentication unless explicitly marked public.
- Tenant isolation — all tenant-scoped data is filtered by the requesting user's tenant unless explicitly bypassed.
- Data visibility — soft-deleted records are hidden from queries unless explicitly requested.
- Response exposure — sensitive fields are excluded from API responses unless explicitly included.

## Rationale

Benefits:

- A forgotten configuration results in a 401 or hidden data, not a data leak.
- Security is not dependent on developer discipline — the framework enforces it.
- Reduces the surface area for security review — only opt-outs need scrutiny.

Tradeoffs:

- Public endpoints require explicit declaration, adding a small amount of ceremony.
- Superuser/cross-tenant operations require explicit bypass, which adds code for legitimate use cases.

Assumptions:

- The vast majority of endpoints are authenticated and tenant-scoped.
- Public endpoints are few and well-known (login, token refresh).
- Legitimate cross-tenant access is rare and limited to platform admins.

Risks:

- Over-restriction could slow development if the opt-out mechanism is cumbersome or poorly documented.

## Alternatives Considered

**Permissive by default, secure by opt-in** — endpoints are public unless explicitly protected.

Rejected because:

- A single forgotten permission class creates a vulnerability.
- Scales poorly — every new endpoint is a risk until someone remembers to secure it.
- Incompatible with enterprise security requirements.

## Consequences

### Positive

- New endpoints are protected without developer action.
- Tenant data isolation is guaranteed unless explicitly overridden.
- Soft-deleted data cannot leak into responses by accident.
- Security audits focus on opt-outs (small, enumerable set) rather than the entire codebase.

### Negative

- Developers must learn how to opt out for legitimate public or cross-tenant use cases.
- Debugging access issues may require understanding which default restriction is blocking the request.

### Risks

- If opt-out mechanisms are undocumented or complex, developers may work around the defaults in unsafe ways.

## Mandatory Rules

- The default behavior is always the most restrictive option. Exposure requires explicit intent.
- All endpoints require authentication by default. Public endpoints must explicitly declare `AllowAny`.
- All tenant-scoped queries filter by the requesting user's tenant. Cross-tenant access requires explicit superuser bypass.
- Soft-deleted records are excluded from default querysets. Inclusion requires explicit intent.
- Sensitive fields are never included in API responses unless the serializer explicitly exposes them.

## Allowed Changes

- Adding new security defaults for emerging concerns (e.g., rate limiting, IP filtering).
- Refining the opt-out mechanism to make legitimate exceptions easier to declare.
- Adding new public endpoints with explicit `AllowAny` declaration.

## Forbidden Changes

- Making any endpoint publicly accessible by default.
- Removing tenant filtering from base querysets without a new ADR.
- Including soft-deleted records in default querysets.
- Exposing sensitive fields (passwords, tokens, internal IDs) in default serializer output.

## Validation Criteria

- An endpoint with no explicit permission configuration returns 401 for unauthenticated requests.
- A tenant-scoped query without explicit bypass never returns records from another tenant.
- A default queryset never includes soft-deleted records.
- Public endpoints are enumerable and documented.

## Related Documents

- [ADR-001: Modular Monolith Architecture](001-modular-monolith-architecture.md)
- [ADR-002: Convention Over Configuration](002-convention-over-configuration.md)

## Future Revisions

- If the platform introduces public-facing APIs (e.g., webhooks, public catalogs), revisit whether a separate permission tier is needed.
- If the opt-out mechanism proves too cumbersome, evaluate simplification without weakening the default posture.
