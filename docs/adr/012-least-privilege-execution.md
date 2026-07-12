# ADR-012: Least Privilege Execution

## Status

Proposed

## Context

The platform runs as a modular monolith where a single deployment serves multiple tenants. The application connects to databases, caches, external services, and internal subsystems. Each of these connections carries permissions — what the connecting identity is allowed to do. Without a governing principle, the path of least resistance is maximum privilege: one database superuser for everything, one service account with full access, one set of credentials shared across all processes.

Maximum privilege is convenient until something goes wrong. A compromised background worker with superuser database access can drop tables. A web process with credentials for every external service leaks all of them if exploited. An admin operation that runs with ambient authority leaves no trace of why elevated access was used.

Previous ADRs establish constraints that demand privilege minimization:

- ADR-004 (Data Boundary Isolation) requires that boundaries are impermeable by default. But if the execution identity has permissions that bypass boundaries (e.g., superuser database access), the boundary enforcement is theater — it exists in application code but not at the infrastructure level.
- ADR-009 (Auditability by Design) requires that operations are traceable. Elevated access that is ambient (always available, never explicitly requested) cannot be meaningfully audited — there is no "elevation event" to record.
- ADR-003 (Least Exposure by Default) governs what the system shows to users. This ADR governs what the system itself is allowed to do.

Constraints:

- Multi-tenant on shared infrastructure — a privilege escalation in one context must not grant access to another tenant's resources.
- Enterprise product — security incidents have legal and reputational consequences proportional to the privilege level compromised.
- Modular monolith — different processes (web, worker, scheduler) may have different legitimate access needs.

Architectural goals affected: security, blast radius containment, auditability, defense in depth.

## Decision

Every component in the system runs with the minimum permissions required to perform its function. Elevated access is scoped to the operation that needs it, temporary in duration, and explicitly justified. Ambient authority — permissions that are always available regardless of whether they are needed — is treated as a security defect.

Three invariants govern this principle:

1. **Default to minimum.** Every process, connection, and service account starts with the least permissions required for its role. Permissions are added explicitly for specific needs, never granted broadly "in case they're needed later."

2. **Elevation is explicit and scoped.** When an operation requires permissions beyond the default, the elevation is a declared, auditable event (per ADR-009) with a defined scope and duration. Elevated access does not persist beyond the operation that justified it.

3. **Separate roles, separate credentials.** Components with different responsibilities (web serving, background processing, administration, migrations) use separate identities with permissions matched to their role. A compromise of one identity does not grant the attacker the permissions of another.

## Rationale

Benefits:

- Blast radius containment — a compromised component can only do what its identity permits, not everything the system can do.
- Defense in depth for boundaries (ADR-004) — even if application-level boundary enforcement has a bug, infrastructure-level permissions limit the damage.
- Auditable elevation — because elevated access is explicit, it produces audit records that can be reviewed.
- Principle of least surprise — a background worker that only has permission to read and write its own queue tables cannot accidentally (or maliciously) modify unrelated data.

Tradeoffs:

- Operational complexity — multiple credentials, multiple database roles, multiple service accounts to manage.
- Development friction — developers cannot use a single superuser connection for everything during local development without diverging from production behavior.
- Permission management overhead — as the system evolves, role permissions must be reviewed and updated.

Assumptions:

- The infrastructure supports fine-grained permission assignment (PostgreSQL roles, scoped API keys, per-process credentials).
- The number of distinct roles is small and grows slowly (web, worker, scheduler, migrator, admin).
- The cost of managing multiple credentials is lower than the cost of a privilege escalation incident.

Risks:

- Over-restriction — permissions too tight for legitimate operations, causing failures that are hard to diagnose (mitigated by ADR-005 — failures are explicit).
- Credential sprawl — too many identities becoming unmanageable without tooling.
- Development/production divergence — developers using broader permissions locally and missing permission-related bugs.

## Alternatives Considered

**Single identity with application-level access control** — one set of credentials for all processes, with access control enforced entirely in application code.

Rejected because:

- A single compromised credential grants access to everything — no blast radius containment.
- Application-level access control is the only defense — a bug in the application means unrestricted access at the infrastructure level.
- Contradicts ADR-004's defense in depth requirement — boundary enforcement exists at only one layer.

**Role-based access at the application layer only, broad infrastructure permissions** — the application enforces who can do what, but the database connection and service accounts have full access.

Rejected because:

- Infrastructure permissions are the last line of defense. If they are maximally permissive, a SQL injection or application bug bypasses all access control.
- Audit of elevated access is impossible if the infrastructure identity always has elevated access — there is no distinction between normal and elevated operations at the infrastructure level.

## Consequences

### Positive

- Compromised components have limited blast radius — damage is contained to the component's permission scope.
- Boundary isolation (ADR-004) is reinforced at the infrastructure level, not just the application level.
- Elevated access is auditable — explicit elevation events are recorded per ADR-009.
- Security posture is verifiable — each component's permissions can be enumerated and reviewed.

### Negative

- Multiple credentials and roles add operational complexity.
- Local development setup is more complex if it mirrors production permission boundaries.
- Permission-related failures require understanding which identity is used by which component.

### Risks

- Credential management becoming a bottleneck if not automated.
- Developers working around permission restrictions during development and introducing bugs that only manifest in production.
- Permission drift — roles accumulating permissions over time without review, gradually approaching the "maximum privilege" state this ADR prohibits.

## Mandatory Rules

- Each distinct process type (web, worker, scheduler, migrator) must use its own identity with permissions scoped to its responsibilities.
- No application process may connect to the database with superuser or owner privileges during normal operation. Migrations are the only exception, and they use a separate, dedicated identity.
- Elevated access (operations requiring permissions beyond the process's default) must be explicitly declared, scoped to the operation, and produce an audit record (per ADR-009).
- Service accounts for external systems must be scoped to the minimum required API surface — no "full access" keys for convenience.
- Credentials must not be shared across process types. A compromise of one process's credentials must not grant access to another process's permissions.

## Allowed Changes

- Defining the specific permission sets for each role as the system's data model and operations evolve.
- Introducing temporary elevation mechanisms (e.g., short-lived tokens for admin operations) that satisfy the "explicit, scoped, auditable" requirements.
- Consolidating roles if two process types are proven to need identical permissions — provided the consolidation is a deliberate decision, not a convenience default.
- Using broader permissions in local development environments — provided CI tests verify permission boundaries match production expectations.

## Forbidden Changes

- Application processes connecting with superuser or owner database credentials during normal operation.
- Sharing credentials across process types with different responsibilities.
- Granting permissions "in case they're needed later" — permissions are added when needed, not preemptively.
- Elevated access that is ambient (always available) rather than explicitly requested per operation.
- Service accounts with broader access than their consuming process requires.

## Validation Criteria

- Each process type's database connection uses a distinct role with enumerable permissions — verifiable by inspecting connection configuration and database role grants.
- No application process connects with superuser privileges — enforceable by database role inspection or connection string auditing in CI.
- Elevated operations produce audit records identifying the elevation justification — verifiable by inspecting audit logs for admin operations.
- Service account permissions are documented and match the minimum required API surface — verifiable by periodic access review.
- A compromise simulation (revoking one process's credentials) does not affect other processes' ability to function — verifiable by integration testing with isolated credentials.

## Related Documents

- [ADR-003: Least Exposure by Default](003-least-exposure-by-default.md)
- [ADR-004: Data Boundary Isolation](004-data-boundary-isolation.md)
- [ADR-009: Auditability by Design](009-auditability-by-design.md)

## Future Revisions

- If the platform introduces microservices or external service boundaries, define how least privilege applies to service-to-service authentication (mTLS, scoped tokens).
- If credential management becomes operationally burdensome, evaluate secrets management tooling (vault, managed identities) as infrastructure support for this principle.
- If the number of distinct roles grows beyond manageable bounds, evaluate role hierarchies or permission inheritance models that maintain least privilege without credential sprawl.
