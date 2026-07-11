# ADR-002: Convention Over Configuration

## Status

Accepted

## Context

The platform supports multiple domain modules that share common concerns: authentication, pagination, filtering, response formatting, soft-delete, timestamps. Each new module needs these capabilities.

Without a guiding principle, each app would configure these concerns independently, leading to inconsistency, boilerplate, and repeated decision-making across the team.

Constraints:

- Enterprise product — consistency across endpoints is a requirement, not a preference.
- Growing number of modules — the cost of per-app configuration scales linearly.
- Small team — cannot afford to re-solve the same problems in every module.

Architectural goals affected: consistency, developer productivity, maintainability.

## Decision

The platform provides sensible defaults for common concerns. Apps receive behavior by default and opt out when needed, rather than opting in to each capability individually.

## Rationale

Benefits:

- New modules start with a working, consistent API without boilerplate setup.
- Common behavior is defined once and applied uniformly — bugs are fixed in one place.
- Reduces decision fatigue — developers focus on domain logic, not infrastructure wiring.

Tradeoffs:

- Implicit behavior requires learning what the defaults are.
- Opting out may require understanding the internals of the default mechanism.

Assumptions:

- Most modules share the same set of common concerns (auth, pagination, filtering, response format, soft-delete).
- The defaults are correct for the majority of cases — opt-out is the exception, not the norm.

Risks:

- If defaults are wrong for many cases, the convention becomes a burden rather than a benefit.
- Developers unfamiliar with the defaults may be surprised by implicit behavior.

## Alternatives Considered

**Explicit configuration per app** — each module wires its own pagination, permissions, filtering, and lifecycle independently. No shared defaults.

Rejected because:

- Leads to inconsistency across apps as the team and codebase grow.
- Boilerplate multiplies with every new endpoint.
- Same bugs must be fixed in multiple places.

## Consequences

### Positive

- Uniform API behavior across all modules without per-app effort.
- New modules are productive immediately — inherit defaults, focus on domain logic.
- Single point of change for cross-cutting behavior.
- Less code — apps only contain domain-specific logic, not infrastructure wiring.
- No reinventing the wheel — solved problems stay solved. Base code is tested once and reused across all modules, reducing the surface area for bugs.

### Negative

- Learning curve — developers must understand what defaults exist and how to override them.
- Debugging requires awareness of inherited behavior that isn't visible in the app's own code.

### Risks

- Over-convention — if too much is implicit, the platform becomes opaque and hard to reason about.

## Mandatory Rules

- Common concerns must have a platform-level default, not per-app configuration.
- Customization is opt-out (override or disable), not opt-in (manually wire up).
- Defaults must be documented so developers know what behavior they inherit.

## Allowed Changes

- Adding new defaults for emerging common concerns.
- Changing the mechanism that delivers defaults (base classes, middleware, plugins) without a new ADR — the principle remains the same.
- Individual apps opting out of specific defaults when justified.

## Forbidden Changes

- Requiring apps to explicitly configure common concerns that have a platform default.
- Removing a default without providing a migration path for existing apps.

## Validation Criteria

- A new app inheriting from the platform's base infrastructure has working authentication, pagination, filtering, and response formatting without any app-level configuration.
- Defaults are documented in a discoverable location.

## Related Documents

- [ADR-001: Modular Monolith Architecture](001-modular-monolith-architecture.md)

## Future Revisions

- If the number of defaults grows to the point where implicit behavior causes frequent confusion, revisit whether some concerns should become opt-in.
- If a module's requirements diverge significantly from the defaults, evaluate whether the convention still serves the platform.
