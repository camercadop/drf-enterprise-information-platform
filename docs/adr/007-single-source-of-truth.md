# ADR-007: Single Source of Truth

## Status

Accepted

## Context

The platform is a modular monolith (ADR-001) where multiple apps coexist in a single codebase and share infrastructure. Knowledge — business rules, data ownership, configuration schema, validation constraints — must be referenced across module boundaries. Without a governing principle, the same knowledge ends up defined in multiple places: a validation rule in one layer and again in another, a business constant in one module and again in a consumer, a configuration default in one file and again in documentation.

Duplication of knowledge creates compounding problems:

- When a rule changes, every copy must be found and updated. Missed copies become silent bugs.
- Contradictions between copies are invisible until they cause production incidents.
- Developers cannot trust any single location as authoritative — they must cross-reference to be sure.
- Configuration driven by data (ADR-006) requires a single authoritative schema — if configuration defaults are scattered, the system cannot validate or enumerate its own behavioral surface.

Constraints:

- Multi-module monolith — knowledge crosses app boundaries, making duplication tempting for convenience.
- Convention-over-configuration (ADR-002) — defaults are defined once and inherited, but the "once" must be enforceable.
- Configuration-driven behavior (ADR-006) — configurable behaviors need a single schema as their source of truth.

Architectural goals affected: maintainability, correctness, auditability of system behavior.

## Decision

Every piece of knowledge in the system is defined in exactly one authoritative location. All other parts of the system derive from or reference that source — they never duplicate it.

Two invariants govern this principle:

1. **One owner per fact.** Every business rule, validation constraint, constant, or schema definition has exactly one canonical location. Other parts of the system that need this knowledge reference or derive from that location.

2. **Derivation over duplication.** When the same knowledge must appear in multiple forms, one is the source and the others are derived — programmatically when possible, by explicit reference when not.

## Rationale

Benefits:

- A change to a rule requires exactly one edit — no hunting for copies.
- The system is self-consistent by construction — contradictions between copies cannot exist if copies do not exist.
- New developers can find the authoritative definition of any concept by following references to their origin.
- Configuration schema (ADR-006) has a single enumerable source, enabling automated validation and documentation generation.

Tradeoffs:

- Cross-module references create coupling — the source module becomes a dependency of its consumers.
- Deriving knowledge programmatically requires tooling investment.
- Some duplication is unavoidable at system boundaries (e.g., client-side validation mirrors server-side rules) — the principle applies within the system's control boundary.

Assumptions:

- The cost of maintaining derived artifacts is lower than the cost of maintaining duplicated knowledge.
- Module boundaries are stable enough that cross-module references do not create excessive churn.
- Knowledge that must cross the system boundary (API contracts consumed by external clients) is managed through versioned schemas, not by duplicating definitions.

Risks:

- Over-centralization — if too much knowledge is pulled into shared modules, those modules become god objects.
- Circular dependencies — if module A owns fact X and module B owns fact Y, but both need each other's facts, the dependency graph becomes tangled.
- Derived artifacts falling out of sync if the derivation pipeline is not automated or enforced in CI.

## Alternatives Considered

**Tolerate controlled duplication with synchronization discipline** — allow copies in multiple locations, rely on code review and documentation to keep them in sync.

Rejected because:

- Synchronization discipline degrades over time — especially under deadline pressure.
- "Controlled duplication" inevitably becomes uncontrolled duplication as the team and codebase grow.
- Contradicts ADR-006 — configuration-driven behavior requires a single authoritative schema, not multiple copies kept in sync by convention.

**Per-module self-contained definitions** — each module defines everything it needs independently, even if it overlaps with other modules.

Rejected because:

- Violates ADR-004 — data ownership means one module owns the definition, others query it.
- Creates drift between modules that should agree on shared concepts.
- Makes cross-module consistency unverifiable.

## Consequences

### Positive

- Single point of change for any business rule, constant, or schema definition.
- Automated documentation and validation can be generated from authoritative sources.
- Contradictions between system components are structurally impossible within the codebase.
- Onboarding is faster — "where is X defined?" always has one answer.

### Negative

- Cross-module references increase coupling between the source module and its consumers.
- Refactoring the authoritative location requires updating all references.
- Derivation tooling must be built and maintained.

### Risks

- Shared modules accumulating too much knowledge and becoming bottlenecks for changes.
- Derivation pipelines that are not enforced in CI silently falling out of sync.
- Developers working around the principle by defining local copies to avoid reference dependencies.

## Mandatory Rules

- No business rule, validation constraint, or domain constant may be defined in more than one location within the codebase.
- When knowledge must appear in multiple forms, one location is designated as the source and others must derive from it — either programmatically or by explicit documented reference.
- Each configurable behavior has its schema and default defined in exactly one location.
- Knowledge consumed by multiple modules is owned by exactly one module — consumers reference, never redefine.

## Allowed Changes

- Moving the authoritative location of a piece of knowledge to a more appropriate module (with corresponding reference updates).
- Adding derivation tooling that generates artifacts from authoritative sources.
- Introducing a shared module for knowledge consumed across multiple apps.
- Accepting boundary duplication (external API contracts, client-side validation) as outside the system's control boundary, provided the internal definition remains the single source.

## Forbidden Changes

- Defining the same business rule, constant, or constraint in multiple locations within the codebase.
- Layers or modules redefining constraints already expressed by the owning source.
- Documentation that hardcodes authoritative values instead of referencing or deriving from the source.
- Configuration defaults for the same behavior scattered across unrelated locations.

## Validation Criteria

- For any given business rule, constant, or constraint, there exists exactly one definition site — all other usages are references or derivations traceable to that site.
- Configuration schema for each configurable behavior is defined in exactly one location.
- No two modules independently define the same domain constant or constraint.

## Related Documents

- [ADR-002: Convention Over Configuration](002-convention-over-configuration.md)
- [ADR-004: Data Boundary Isolation](004-data-boundary-isolation.md)
- [ADR-006: Behavior Driven by Configuration](006-behavior-driven-by-configuration.md)

## Future Revisions

- If cross-module coupling from shared references becomes a maintenance burden, revisit whether an event-based or interface-based decoupling layer is warranted.
- If derivation tooling proves too costly to maintain, evaluate whether explicit documented references (non-automated) are an acceptable alternative for low-churn knowledge.
- If the system boundary expands (e.g., shared libraries consumed by external services), define how the single-source principle applies across repository boundaries.
