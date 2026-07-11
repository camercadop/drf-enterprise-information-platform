# ADR-004: Data Boundary Isolation

## Status

Accepted

## Context

The platform manages data that belongs to different logical owners — tenants, users, the platform itself, and potentially other groupings as the system evolves. A single piece of data exposed to the wrong owner constitutes a breach, regardless of whether the owner is a tenant, a user, or any other entity.

Previous ADRs establish that the platform defaults to the most restrictive posture (ADR-003) and provides sensible defaults without per-app configuration (ADR-002). However, neither defines the fundamental rules governing how data ownership and visibility work across the system.

Without a unifying principle, each isolation concern (tenant filtering, user-scoped data, role-based visibility) would be designed independently, with inconsistent rigor and different failure characteristics.

Constraints:

- Enterprise product — any data leak has legal and reputational consequences, regardless of which boundary was breached.
- Multiple isolation concerns coexist — tenant isolation, user isolation, and potentially others.
- The system grows over time — new boundaries may emerge as new domains are added.

Architectural goals affected: security, data integrity, consistency, evolvability.

## Decision

The platform adopts "boundary" as the core abstraction for data ownership and visibility. A boundary is a logical perimeter that owns data and controls who can see it.

Five invariants govern all boundaries in the system:

1. **Data belongs to a boundary.** Every resource in the system has a clear owner. There is no ambiguous or unowned data.

2. **Boundaries are impermeable by default.** Data does not cross its boundary unless explicitly allowed. The default answer to "can X see Y?" is no.

3. **All boundaries get defense in depth.** No single point of failure can breach any boundary. Multiple independent mechanisms must fail simultaneously for data to leak. This applies equally to all boundaries regardless of perceived risk.

4. **Unknown context means denial.** If the system cannot determine which boundary a request operates within, the operation is denied. Ambiguity is never resolved by guessing.

5. **Boundary crossing is explicit and auditable.** Legitimate cross-boundary access exists but requires declared intent, is never the default path, and leaves a trace.

This ADR does not enumerate which boundaries exist in the system — that is a data modeling concern. It establishes the rules that any boundary, present or future, must satisfy.

## Rationale

Benefits:

- Universal rules eliminate judgment calls about "how much isolation does this boundary need."
- Consistent with ADR-003 — the most restrictive posture is always the default, applied uniformly.
- New boundaries inherit the same guarantees without new architectural decisions about rigor.
- Defense in depth means a single missed check (a forgotten permission, a wrong queryset) cannot cause a breach.

Tradeoffs:

- Every boundary requires multiple enforcement layers, even for low-risk cases. This adds implementation cost.
- Legitimate cross-boundary operations require explicit ceremony at every layer.

Assumptions:

- The set of boundary types is small and grows slowly.
- Cross-boundary access is the exception, not the norm.
- The cost of redundant enforcement is small compared to the cost of a breach.

Risks:

- If the enforcement ceremony is too heavy, developers may find workarounds that undermine the principles.

## Alternatives Considered

**Risk-proportional isolation** — boundaries with lower perceived risk (e.g., user-to-user within the same tenant) get fewer enforcement layers than high-risk boundaries (e.g., tenant-to-tenant).

Rejected because:

- Introduces subjective judgment about what's "risky enough" — different developers will answer differently.
- Contradicts ADR-003's uniform restrictive posture.
- A boundary considered low-risk today may become high-risk as the system evolves (e.g., when sensitive data is added to a previously innocuous resource).
- After an incident, "we thought this boundary was low-risk" is not an acceptable explanation.

**Per-concern isolation design** — each isolation concern (tenants, users, roles) is designed independently with its own rules and rigor.

Rejected because:

- Leads to inconsistent guarantees across the system.
- No shared vocabulary for reasoning about isolation.
- Each new concern requires a full architectural discussion about enforcement strategy.

## Consequences

### Positive

- Every boundary in the system has the same guarantees — no weak links.
- A single missed enforcement mechanism cannot cause a data leak.
- New boundaries (future domains, new entity types) inherit the same principles without new ADRs.
- Cross-boundary access is always visible and traceable.
- The system fails closed — ambiguity results in denial, not exposure.

### Negative

- All boundaries require multiple enforcement layers, adding implementation effort even for seemingly low-risk cases.
- Cross-boundary operations require explicit bypass at every layer, which adds code for legitimate use cases.
- Developers must understand the boundary model to work effectively with the system.

### Risks

- If the bypass mechanism is too cumbersome, developers may circumvent boundaries in unsafe ways.
- Over-engineering isolation for truly low-risk boundaries could slow development without meaningful security benefit.

## Mandatory Rules

- Every resource must belong to exactly one boundary. No resource exists without a clear owner.
- Boundaries are impermeable by default. Data visibility across a boundary requires explicit opt-in.
- Every boundary must be enforced by at least two independent mechanisms. A failure in one mechanism must not be sufficient to breach the boundary.
- Operations with ambiguous or missing boundary context must be denied. The system never infers or guesses boundary membership.
- Cross-boundary access must be explicitly declared and produce an auditable record.

## Allowed Changes

- Defining new boundary types as the system evolves.
- Adding enforcement mechanisms to existing boundaries (strengthening isolation).
- Refining the cross-boundary bypass mechanism to reduce ceremony without weakening guarantees.
- Defining which specific mechanisms satisfy "defense in depth" for each boundary type (in implementation-level ADRs or guidelines).

## Forbidden Changes

- Allowing any boundary to be enforced by a single mechanism only.
- Making cross-boundary access implicit or silent.
- Allowing resources to exist without a declared boundary owner.
- Resolving ambiguous boundary context by guessing or defaulting to a permissive interpretation.
- Exempting a boundary from defense in depth based on perceived risk.

## Validation Criteria

- Every model in the system can be traced to a boundary owner.
- For each boundary type, at least two independent enforcement mechanisms can be identified.
- A request with missing or ambiguous boundary context results in denial (not data exposure).
- Cross-boundary access operations produce auditable records.
- Disabling any single enforcement mechanism for a boundary does not expose data across that boundary.

## Related Documents

- [ADR-002: Convention Over Configuration](002-convention-over-configuration.md)
- [ADR-003: Least Exposure by Default](003-least-exposure-by-default.md)

## Future Revisions

- Once the system's boundary types are enumerated (tenant, user, platform, etc.), a data model document or subsequent ADR should map each resource to its boundary.
- If the enforcement ceremony proves too heavy for specific boundaries, evaluate simplification without violating the "two independent mechanisms" invariant.
- If the system introduces boundaries that nest (e.g., user within tenant within platform), a subsequent ADR may define rules for hierarchical boundary relationships.
