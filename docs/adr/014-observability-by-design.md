# ADR-014: Observability by Design

## Status

Proposed

## Context

The platform is a multi-tenant enterprise system running on shared infrastructure. At any point in time, multiple tenants are executing operations concurrently. When something goes wrong — a slow endpoint, a spike in errors, a background task that silently stalls — the first question is: what is the system doing right now, and what was it doing when the problem started?

Without a governing principle, observability is added reactively — a metric here when a performance problem is discovered, a trace there when a bug is hard to reproduce. The result is instrumentation that covers the paths that have already failed, not the paths that are about to fail. Gaps are invisible until they become incidents.

Previous ADRs establish constraints that observability depends on:

- ADR-005 requires that failures are explicit — but explicit failures are only actionable if the system provides enough context to understand them. A logged exception without a trace, a tenant ID, or a request ID is explicit but not diagnosable.
- ADR-009 requires auditability of state changes — but auditability answers "what changed," not "why the system behaved the way it did." Observability covers the operational dimension: latency, throughput, error rates, resource consumption.
- ADR-006 requires that the same artifact runs in all environments — which means instrumentation must be present in all environments, not added only in production after a problem surfaces.

Constraints:

- Multi-tenant on shared infrastructure — a performance degradation affecting one tenant must be distinguishable from one affecting all tenants.
- Enterprise product — SLA commitments require the ability to detect and diagnose degradation before customers report it.
- Modular monolith — a single deployment serves all domains; without instrumentation, it is impossible to attribute resource consumption or latency to a specific module or operation.

Architectural goals affected: operational confidence, debuggability, reliability, capacity planning.

## Decision

Observability is a design requirement, not an operational add-on. The system must be understandable from its external outputs at all times — not only after a problem has been discovered.

Three invariants govern this principle:

1. **Instrumentation is structural, not incidental.** The platform's shared infrastructure emits signals for all operations by default. A new module inherits observability without any module-level effort — it does not opt in.

2. **Every operation carries a traceable identity.** Each operation entering the system is assigned a correlation identity that flows through every layer it touches. Diagnosing a problem never requires reconstructing a timeline from disconnected outputs.

3. **Signals are tenant-aware.** Operational signals carry tenant context where it exists. A platform-wide anomaly can be decomposed by tenant — attributed to a specific workload, not just to "the system."

## Rationale

Benefits:

- Problems are detected from signals, not from customer reports — the system reveals its own degradation.
- Diagnosing an incident starts from a trace, not from log archaeology across disconnected outputs.
- Capacity planning is grounded in measured behavior, not estimates — the system's actual resource consumption per operation is known.
- New modules are observable by default — no per-module instrumentation effort required.

Tradeoffs:

- Instrumentation adds overhead to every operation — trace context propagation, metric recording, and structured log emission have a cost.
- Observability infrastructure (collectors, storage, dashboards) must be operated alongside the application — it is not free.
- Tenant-aware signals require tenant context to be available at every instrumentation point — this couples observability to the tenant context propagation mechanism.

Assumptions:

- The overhead of instrumentation is acceptable relative to the operational value it provides.
- Shared infrastructure is the right layer to own instrumentation — not individual modules.
- Tenant context is reliably available at signal emission points (per ADR-009's context propagation requirement).

Risks:

- Instrumentation overhead becoming a performance concern at high request volumes.
- Signals containing sensitive tenant data — observability data requires the same access control and retention governance as application data.
- Signal noise making the useful signal undetectable if instrumentation is not purposeful.

## Alternatives Considered

**Reactive instrumentation — add observability when problems occur** — instrument specific paths after a problem is discovered.

Rejected because:

- The paths that fail in production are not always the paths that were instrumented during development.
- Reactive instrumentation requires a deployment to diagnose a live incident — the system is blind precisely when visibility matters most.
- Contradicts ADR-006 — the artifact running in production must be the same as the one in staging; adding instrumentation only in production violates environment parity.

**Per-module instrumentation — each module owns its own observability** — developers add metrics and traces to their modules independently.

Rejected because:

- Violates ADR-002 — common concerns have platform defaults, not per-module decisions.
- Results in inconsistent coverage — modules built under deadline pressure will have less instrumentation than modules built with time to spare.
- Cross-module traces require consistent instrumentation conventions; per-module ownership makes this impossible to enforce.

## Consequences

### Positive

- System behavior is visible without a deployment to add instrumentation.
- Incidents are diagnosable from recorded signals — no need to reproduce conditions.
- New modules inherit observability without additional effort.

### Negative

- Instrumentation overhead is always present — the cost is paid regardless of whether anyone is monitoring.
- Observability infrastructure must be operated alongside the application.
- Signals containing sensitive data require governance — retention and access control apply.

### Risks

- Sampling strategies that reduce overhead may also reduce visibility precisely when load is highest.
- Missing tenant context on a signal makes it unattributable — partial observability can create false confidence.
- Observability infrastructure failure causes silent signal loss.

## Mandatory Rules

- The platform's base infrastructure must emit traces, metrics, and structured logs for all inbound requests and outbound operations without per-module configuration.
- Every trace must carry a correlation identity that links all operations — database queries, cache calls, background tasks — triggered by a single inbound request.
- Observability signals must carry tenant context wherever tenant context exists. Signals emitted without available tenant context must be explicitly marked as platform-level, not silently attributed to a default tenant.
- Instrumentation must be present in all environments — not added only in production. The same artifact runs everywhere (per ADR-006).

## Allowed Changes

- Adjusting sampling rates for high-volume, low-risk operations to manage overhead — provided sampling decisions are explicit and documented, not silent.
- Extending the set of signals emitted by the base infrastructure as new operational concerns emerge.
- Varying signal detail by operation category (e.g., full traces for write operations, sampled traces for reads) — provided the sampling strategy is declared and consistent.
- Adding module-specific signals on top of the platform baseline — provided they follow the same conventions (tenant context, correlation identity, structured format).

## Forbidden Changes

- Disabling instrumentation in any environment, including local development and CI.
- Emitting observability signals without tenant context in contexts where tenant context is available.
- Adding per-module instrumentation that deviates from the platform's signal conventions (naming, context fields, format).
- Treating observability as optional for new modules — every module built on the platform's base infrastructure inherits instrumentation unconditionally.

## Validation Criteria

- Every inbound HTTP request produces a trace — verifiable by asserting trace output in integration tests for any endpoint.
- Traces for authenticated requests include a tenant identifier attribute — assertable via integration test trace inspection.
- A module with no instrumentation code of its own emits signals by virtue of the platform's base infrastructure — verifiable by adding a minimal module and confirming signal output without module-level additions.
- No environment configuration disables instrumentation — enforceable by CI asserting that observability infrastructure is present in all environment configurations.

## Related Documents

- [ADR-002: Convention Over Configuration](002-convention-over-configuration.md)
- [ADR-005: Explicit Over Implicit Failure](005-explicit-over-implicit-failure.md)
- [ADR-006: Behavior Driven by Configuration](006-behavior-driven-by-configuration.md)
- [ADR-009: Auditability by Design](009-auditability-by-design.md)

## Future Revisions

- If instrumentation overhead becomes a measurable performance concern, define a formal sampling policy as a follow-up ADR rather than making ad-hoc sampling decisions per module.
- If observability data retention becomes a cost or compliance concern, define a tiered retention strategy that applies uniformly across all signal types.
- If the platform introduces non-HTTP entry points (WebSocket, gRPC, message queue consumers), define how the correlation identity and tenant context invariants apply to those entry points.
