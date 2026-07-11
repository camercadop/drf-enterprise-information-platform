# ADR-006: Behavior Driven by Configuration

## Status

Proposed

## Context

The platform serves multiple tenants from a single deployment (ADR-001). Each tenant may require different feature sets, workflow variations, or behavioral constraints. Without a governing principle, these differences manifest as conditional code paths — `if tenant == X`, `if environment == Y`, feature flags buried in business logic, or forked implementations per customer.

Conditional branching per tenant or environment creates compounding problems:

- Every new tenant variation adds code paths that must be tested in combination with all others.
- Environment-specific branches mean the binary running in staging is not the same binary running in production — it just happens to share a codebase.
- Per-tenant code forks make it impossible to reason about system behavior without knowing which tenant is active.
- Disabling a feature requires a deployment rather than a configuration change.

Constraints:

- Multi-tenant — tenant-specific behavior is inevitable, but per-tenant code is not sustainable.
- Modular monolith — a single deployable artifact must serve all tenants and environments.
- Enterprise product — customers expect customization without waiting for code releases.

Architectural goals affected: scalability of tenant onboarding, deployability, testability, operational simplicity.

## Decision

Code defines what is possible. Configuration determines what is active. The system adapts to tenants, environments, and operational needs through data — never through conditional code paths or hardcoded special cases.

The same binary runs in all environments and for all tenants. Behavioral differences between tenants or environments are expressed exclusively as configuration values consumed by generic, parameterized code paths.

Four invariants govern this principle:

1. **No identity-based branching.** Business logic never conditions on tenant identity, environment name, or user identity to select behavior. Logic conditions on capabilities, feature flags, or configuration values — which happen to differ per tenant or environment.

2. **Configuration is explicit and declarative.** Every configurable behavior has a named setting with a documented default. The set of possible behaviors is knowable by inspecting configuration schema, not by reading code branches.

3. **Feature activation is a data change.** Enabling or disabling a capability for a tenant is a configuration update, not a code deployment. The code for the capability exists unconditionally — configuration determines whether it executes.

4. **Environment parity.** The deployed artifact is identical across environments. Environment-specific behavior (database URLs, cache backends, external service endpoints) is injected via environment configuration, never compiled into the application.

## Rationale

Benefits:

- Tenant onboarding scales without code changes — new tenants get a configuration profile, not a code branch.
- The binary in staging is the binary in production — environment differences are limited to infrastructure configuration.
- Feature rollout and rollback are operational actions, not deployment events.
- The system's behavioral surface is enumerable — inspect configuration schema to know what can vary.

Tradeoffs:

- Requires upfront investment in configuration schema design and validation.
- Some behaviors that would be trivial as an `if` statement require more structured implementation (strategy patterns, plugin registration).
- Configuration drift between tenants becomes a management concern — requires tooling to audit and compare.

Assumptions:

- The number of tenants will grow — per-tenant code paths do not scale.
- Most "custom" requirements are combinations of generic capabilities, not truly unique logic.
- Configuration is validated at startup or request time (per ADR-005 — misconfiguration is a crash).

Risks:

- Over-configuration — making everything configurable creates a system that is hard to understand and easy to misconfigure.
- Configuration becomes implicit code — complex configuration interactions can be as hard to reason about as code branches.
- Performance overhead if configuration is evaluated per-request without caching.

## Alternatives Considered

**Per-tenant code branches** — `if tenant.slug == "acme"` guards around custom behavior.

Rejected because:

- Does not scale — each new tenant adds branches that interact combinatorially.
- Violates ADR-001 — the monolith becomes a collection of per-tenant forks sharing a process.
- Untestable in isolation — you cannot verify "acme" behavior without activating the acme context.

**Separate deployments per tenant** — each tenant gets their own instance with custom code.

Rejected because:

- Contradicts the shared-infrastructure model (ADR-001, ADR-004).
- Operational cost scales linearly with tenant count.
- Bug fixes must be applied N times instead of once.

**Feature flags as ad-hoc conditionals** — boolean flags checked inline wherever behavior diverges.

Rejected because:

- Without structure, flags proliferate and interact unpredictably.
- Flags buried in business logic are indistinguishable from the per-tenant branching they replace.
- This ADR does not reject feature flags — it requires them to be part of a declared configuration schema, not ad-hoc inline checks.

## Consequences

### Positive

- Single artifact deployment — what runs in CI is what runs in production.
- Tenant onboarding is an operational task, not a development task.
- Behavioral differences are auditable — compare configuration profiles, not code paths.
- Testing is simplified — test the generic capability once, not per-tenant variations of it.

### Negative

- Initial implementation cost is higher — generic, parameterized code requires more design than a quick `if` branch.
- Configuration schema must be maintained and documented as a first-class artifact.
- Debugging requires understanding which configuration values are active, adding a layer of indirection.

### Risks

- Configuration complexity can rival code complexity if not actively managed.
- Stale or unused configuration values accumulate without cleanup discipline.
- If configuration validation is weak, invalid combinations may not surface until runtime (mitigated by ADR-005).

## Mandatory Rules

- No business logic may condition on tenant identity, environment name, or user identity to select a code path. Conditions must reference capabilities or configuration values.
- Every configurable behavior must have a declared default value and be documented in the configuration schema.
- The deployed artifact must be identical across all environments. No compile-time or build-time environment specialization.
- Enabling or disabling a feature for a tenant must not require a code change or deployment.
- Configuration values must be validated at startup or first use — invalid configuration is a crash (per ADR-005).

## Allowed Changes

- Adding new configuration keys with sensible defaults (existing tenants are unaffected).
- Introducing configuration profiles or presets that bundle common combinations.
- Adding configuration validation rules that reject invalid combinations.
- Implementing configuration inheritance (tenant inherits from a base profile, overrides specific values).

## Forbidden Changes

- Adding `if tenant == X` or `if environment == Y` conditions in business logic.
- Deploying different code to different environments (beyond infrastructure configuration injection).
- Introducing configurable behavior without a declared default and schema entry.
- Hardcoding feature availability to specific tenants by identity.
- Requiring a code deployment to change tenant-specific behavior that is within the configured capability set.

## Validation Criteria

- `grep -rn "tenant.*slug\|tenant.*name\|tenant.*id" --include="*.py" apps/` in business logic (excluding permission/filtering layers) returns zero identity-based branching.
- `grep -rn "settings\.ENV\|settings\.ENVIRONMENT" --include="*.py" apps/` returns zero environment-based branching in application code.
- Every feature flag or configurable behavior has a corresponding entry in the configuration schema with a default value.
- The same Docker image is deployed to all environments — CI can verify image digest equality.
- Tenant onboarding can be completed without modifying Python source files (verifiable via integration test).

## Related Documents

- [ADR-001: Modular Monolith Architecture](001-modular-monolith-architecture.md)
- [ADR-004: Data Boundary Isolation](004-data-boundary-isolation.md)
- [ADR-005: Explicit Over Implicit Failure](005-explicit-over-implicit-failure.md)

## Future Revisions

- If tenant requirements diverge beyond what parameterized configuration can express, revisit whether a plugin-per-tenant model (code as configuration) is warranted.
- If configuration schema grows beyond manageable size, consider splitting into domain-scoped configuration modules with independent validation.
- If real-time configuration changes (without restart) become necessary, define the hot-reload contract and its interaction with ADR-005 validation guarantees.
