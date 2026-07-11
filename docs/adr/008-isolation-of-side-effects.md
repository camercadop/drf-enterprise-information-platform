# ADR-008: Isolation of Side Effects

## Status

Accepted

## Context

The platform is a modular monolith (ADR-001) where business operations frequently trigger secondary actions: sending notifications, emitting events, calling external services, writing audit records, updating caches. When these side effects are interleaved with core business logic, several problems emerge:

- Business rules become untestable without mocking I/O — test suites are slow, brittle, and coupled to infrastructure.
- The order and conditions under which side effects fire are implicit — buried inside validation methods, model save overrides, or serializer logic.
- Failures in side effects (a notification service is down, an external API times out) cascade into the primary operation, or worse, are silently swallowed to avoid blocking the main path.
- Reasoning about "what happens when X is created" requires reading through multiple layers to discover hidden triggers.

Previous ADRs establish relevant constraints:

- ADR-005 requires that failures are explicit and atomic — a side effect that fails silently violates this principle, and one that fails loudly inside business logic couples unrelated concerns.
- ADR-002 establishes convention-over-configuration — side effect attachment points should be predictable and uniform, not ad-hoc per operation.
- ADR-007 requires single source of truth — the definition of "what side effects an operation triggers" should be discoverable in one place, not scattered across layers.

Constraints:

- Enterprise product — side effects include legally required actions (audit trails, compliance notifications) that must be reliable.
- Multi-tenant — a side effect triggered in one tenant's context must never leak into another's.
- Plugin architecture — the platform already uses a plugin system for cross-cutting concerns, establishing a precedent for separated behavior.

Architectural goals affected: testability, debuggability, correctness, maintainability.

## Decision

Side effects are separated from pure business logic and occur only at well-defined, predictable points in the operation lifecycle. Business logic determines what should happen. Side effects determine how the world is notified.

Three invariants govern this principle:

1. **Business logic is pure of I/O.** The core decision-making — validation, state transitions, rule evaluation — does not perform I/O, send notifications, or call external systems. It computes the result; it does not broadcast it.

2. **Side effects live at declared boundaries.** Side effects execute at explicit lifecycle points (hooks, plugins, signals) that are architecturally defined and discoverable. A developer reading the business logic can understand the operation's correctness without knowing what side effects are attached.

3. **Side effect failure does not corrupt the primary operation's correctness.** A side effect that fails is handled according to its own contract — retried, logged, or escalated — but the primary operation's state remains consistent. The boundary between "the thing happened" and "the world was told" is explicit.

## Rationale

Benefits:

- Business rules are testable with no I/O setup — fast, deterministic unit tests.
- Side effects are enumerable — "what happens when X is created" is answerable by inspecting lifecycle hooks, not by reading all code paths.
- Failures in secondary systems (email, webhooks, external APIs) do not corrupt primary data operations.
- New side effects are added by attaching behavior at lifecycle points, not by modifying business logic.

Tradeoffs:

- Strict separation requires discipline — the temptation to "just add a quick call here" inside business logic is constant.
- Some operations have side effects that feel inseparable from the business logic (e.g., "creating a user means sending a welcome email") — the separation is still enforced, even when it feels ceremonial.
- Lifecycle hooks add indirection — understanding the full picture requires knowing where to look.

Assumptions:

- The platform's lifecycle hooks (pre/do/post pattern, plugins) provide sufficient attachment points for all required side effects.
- Side effects that must be transactionally consistent with the primary operation (e.g., audit records) can share the database transaction without violating the separation — they are still declared at boundaries, not inline.
- Most side effects are eventually-consistent with the primary operation — a brief delay between "user created" and "welcome email sent" is acceptable.

Risks:

- Over-isolation — if side effects are too decoupled, it becomes hard to guarantee that required actions (audit, compliance) actually fire.
- Lifecycle hook proliferation — too many attachment points make the system harder to reason about than inline code would be.
- Developers circumventing the principle by treating model save() overrides as "lifecycle hooks" when they are actually inline side effects.

## Alternatives Considered

**Inline side effects with try/catch isolation** — side effects execute inline within business logic but are wrapped in error handling to prevent cascade failures.

Rejected because:

- Business logic becomes cluttered with unrelated concerns — readability and testability degrade.
- Error handling for side effects obscures the primary operation's flow.
- Violates ADR-007 — the "what triggers what" knowledge is scattered across business logic methods rather than declared in one discoverable location.

**Event-driven architecture with full async decoupling** — all side effects are triggered via an event bus, fully decoupled from the primary operation.

Rejected because:

- Adds infrastructure complexity disproportionate to the current scale (modular monolith, not microservices).
- Makes it harder to guarantee that mandatory side effects (audit) actually execute — eventual consistency for compliance-critical actions introduces risk.
- Does not preclude future adoption — the principle of isolation is compatible with migrating to event-driven delivery later.

## Consequences

### Positive

- Business logic is testable without I/O mocking — unit tests are fast and deterministic.
- Side effects are discoverable — inspecting lifecycle hooks reveals the full picture of an operation's consequences.
- Adding or removing a side effect does not require modifying business logic.
- Failures in external systems do not corrupt primary data operations.

### Negative

- Indirection — understanding the complete behavior of an operation requires inspecting both the business logic and its attached side effects.
- Discipline cost — developers must resist the convenience of inline side effects.
- Some operations feel artificially split when the side effect is conceptually inseparable from the action.

### Risks

- Mandatory side effects (audit, compliance) that are "attached" rather than "inline" could be accidentally detached — validation must ensure required hooks are present.
- If lifecycle points are poorly documented, the discoverability benefit is lost.
- Performance-sensitive operations may suffer if side effects execute synchronously at lifecycle boundaries — async execution strategies must be considered per case.

## Mandatory Rules

- Business logic methods (validation, state transitions, rule evaluation) must not perform I/O, send notifications, or call external services directly.
- Side effects must execute at architecturally defined lifecycle points — not inside model methods, serializer validation, or permission checks.
- The set of side effects attached to an operation must be discoverable by inspecting the operation's lifecycle configuration — not by reading through implementation code.
- Side effect failure handling must be explicit — either the side effect participates in the operation's transaction (and its failure aborts the operation per ADR-005), or it is explicitly declared as non-blocking with its own failure strategy.

## Allowed Changes

- Introducing new lifecycle attachment points as the platform's operation patterns evolve.
- Defining categories of side effects (transactional vs. eventual, mandatory vs. optional) with different failure semantics.
- Migrating specific side effects from synchronous lifecycle hooks to async execution (queues, events) without changing the principle.
- Side effects that share the primary operation's database transaction (e.g., audit records written in the same commit) — provided they are still declared at lifecycle boundaries, not inline in business logic.

## Forbidden Changes

- Performing I/O (network calls, file writes, external service calls) inside business logic methods that compute state transitions or validate rules.
- Hiding side effects inside model save()/delete() overrides, serializer validate() methods, or permission check() methods.
- Silently swallowing side effect failures — every failure must produce a signal per ADR-005.
- Making side effects undiscoverable — if a developer cannot enumerate an operation's side effects without reading all implementation code, the principle is violated.

## Validation Criteria

- Business logic classes (services, domain methods) contain no direct I/O calls — enforceable by architectural tests that inspect imports or by module-level dependency rules.
- Every side effect is attached at a declared lifecycle point (hook, plugin, signal) — not called inline from business logic.
- For any operation, the complete list of side effects can be determined by inspecting lifecycle configuration without reading the operation's internal implementation.
- Side effect failures produce explicit signals (exceptions, error logs, retry queue entries) — no silent swallowing.

## Related Documents

- [ADR-002: Convention Over Configuration](002-convention-over-configuration.md)
- [ADR-005: Explicit Over Implicit Failure](005-explicit-over-implicit-failure.md)
- [ADR-007: Single Source of Truth](007-single-source-of-truth.md)

## Future Revisions

- If the platform adopts an event bus or message broker, revisit whether event-driven delivery should become the default mechanism for non-transactional side effects.
- If the number of lifecycle attachment points grows unwieldy, evaluate consolidation or a registry pattern for side effect declaration.
- If mandatory side effects (audit, compliance) are found to be accidentally omitted in practice, introduce compile-time or startup-time verification that required hooks are registered.
