# ADR-010: Bounded Operations

## Status

Accepted

## Context

The platform serves multiple tenants on shared infrastructure. A single unbounded operation — a query that returns every row, a bulk import with no size limit, an external call with no timeout — can exhaust shared resources and degrade service for all tenants. Unbounded operations are a category of silent failure: the system does not crash, but it becomes unusable.

Previous ADRs establish constraints that make unbounded operations architecturally incompatible:

- ADR-005 requires that failures are explicit and early. An operation that silently degrades performance or times out after minutes is not failing fast — it is failing slowly and invisibly.
- ADR-004 requires boundary isolation. An unbounded operation in one tenant's context that starves shared resources effectively breaches other tenants' boundaries — not through data leakage, but through resource starvation.
- ADR-008 requires that side effects are predictable. An operation whose resource consumption is unbounded has unpredictable impact on the system — its "side effect" on shared infrastructure is neither declared nor controlled.

Constraints:

- Multi-tenant on shared infrastructure — one tenant's workload must not degrade another's experience.
- Enterprise product — predictable response times and resource usage are operational requirements.
- Modular monolith — no per-tenant resource isolation at the infrastructure level; isolation must be enforced at the application layer.

Architectural goals affected: reliability, fairness, predictability, operational stability.

## Decision

Every operation in the system has explicit limits on time, size, and resource consumption. Unbounded operations are architecturally forbidden. When a limit is reached, the operation fails explicitly (per ADR-005) rather than degrading silently.

Three invariants govern this principle:

1. **Every query has a result ceiling.** No operation returns an unbounded result set. Pagination is mandatory for collection endpoints. Internal queries that aggregate or iterate have explicit row limits.

2. **Every external interaction has a time budget.** No operation waits indefinitely for an external system (database, cache, third-party API, internal service). Timeouts are explicit and declared, not inherited from infrastructure defaults.

3. **Every bulk operation has a batch boundary.** Operations that process multiple items (imports, exports, batch updates) have explicit size limits. Exceeding the limit is a rejection, not a silent truncation.

## Rationale

Benefits:

- Resource consumption is predictable — capacity planning is possible because operations have known upper bounds.
- Multi-tenant fairness — no single operation can monopolize shared resources.
- Failures are fast and explicit — a timeout or size rejection is immediate and actionable, not a slow degradation discovered minutes later.
- Operational confidence — the system's worst-case behavior is bounded and known.

Tradeoffs:

- Legitimate large operations (full exports, bulk migrations) require explicit design — they cannot be naive unbounded loops.
- Limits must be chosen and maintained — too tight and they reject valid operations; too loose and they fail to protect.
- Adds configuration surface — every operation category needs its bounds defined somewhere.

Assumptions:

- Reasonable upper bounds exist for every operation in the system — no operation legitimately needs unbounded resources.
- Clients can handle paginated results and chunked bulk operations.
- Limits are defined per operation category, not per individual request — the system does not need per-request negotiation.

Risks:

- Limits set too conservatively frustrate legitimate use cases and push users toward workarounds.
- Limits set too generously fail to protect shared resources when they matter most.
- Limit values scattered across the codebase become hard to discover and maintain (mitigated by ADR-007 — single source of truth for configuration).

## Alternatives Considered

**Resource quotas per tenant instead of per-operation limits** — each tenant gets a resource budget (CPU time, query count, storage) and can use it however they want within that budget.

Rejected because:

- Does not prevent a single operation from consuming the entire quota in one request — the system still needs per-operation bounds.
- Quota enforcement is complex infrastructure that does not eliminate the need for operation-level limits.
- Does not address the core problem: an individual operation with no ceiling is unpredictable regardless of who runs it.

**Soft limits with degradation warnings** — operations that exceed thresholds log warnings and continue, only hard-failing at extreme values.

Rejected because:

- Violates ADR-005 — a warning that is ignored is a silent failure. The operation either succeeds within bounds or fails explicitly.
- "Soft limits" become the actual limits in practice — the hard limit is never reached because the system has already degraded.
- Warnings accumulate and are ignored, providing no operational value.

## Consequences

### Positive

- The system's worst-case resource consumption per operation is known and bounded.
- Multi-tenant fairness is enforced at the application layer without infrastructure-level isolation.
- Capacity planning is tractable — bounded operations have predictable resource profiles.
- Failures from exceeding limits are immediate and informative, not slow degradations.

### Negative

- Large legitimate operations require chunked/paginated design — no "just get everything" convenience.
- Limit values must be chosen, documented, and maintained — an ongoing configuration concern.
- Some operations that would "probably be fine" unbounded are now constrained, adding friction.

### Risks

- Poorly chosen limits causing false rejections that erode trust in the system.
- Limit configuration becoming scattered if not governed by ADR-007's single source of truth principle.
- Edge cases where the "right" limit depends on context (tenant size, data volume) requiring per-tenant configuration that adds complexity.

## Mandatory Rules

- No API endpoint may return an unbounded collection. All collection responses must be paginated with a maximum page size.
- All external calls (database queries, HTTP requests, cache operations) must have explicit timeouts. No operation may wait indefinitely.
- Bulk operations must declare and enforce a maximum batch size. Submissions exceeding the limit must be rejected, not silently truncated.
- Exceeding any operational limit must produce an explicit error response (per ADR-005) — never silent truncation, silent degradation, or a warning-and-continue.
- Internal queries that iterate or aggregate must have explicit row limits or be structured as bounded batches.

## Allowed Changes

- Adjusting limit values as operational experience reveals appropriate thresholds.
- Defining per-tenant limit overrides for specific operation categories — provided the override is explicit configuration (per ADR-006), not a code branch.
- Introducing tiered limits (e.g., higher batch sizes for background operations vs. synchronous API requests) — provided all tiers have explicit ceilings.
- Adding new limit categories as new operation types emerge.

## Forbidden Changes

- Removing pagination from any collection endpoint.
- Allowing any external call to execute without an explicit timeout.
- Silently truncating results that exceed a limit instead of returning an explicit error.
- Introducing unbounded loops or queries that iterate without a declared ceiling.
- Treating warnings as acceptable substitutes for hard limits on resource consumption.

## Validation Criteria

- Every collection endpoint returns paginated results with a declared maximum page size — enforceable by inspecting view configurations or integration tests.
- Every external call (HTTP, database, cache) has an explicit timeout configured — enforceable by architectural tests or middleware inspection.
- Bulk operation endpoints reject payloads exceeding the declared batch size with an appropriate error response — verifiable via integration tests.
- No query in the codebase uses unbounded iteration (e.g., `.all()` without slicing in a loop context) — enforceable via linting or architectural tests.
- Exceeding any limit produces an HTTP 4xx error with a message identifying which limit was exceeded and what the maximum is.

## Related Documents

- [ADR-004: Data Boundary Isolation](004-data-boundary-isolation.md)
- [ADR-005: Explicit Over Implicit Failure](005-explicit-over-implicit-failure.md)
- [ADR-008: Isolation of Side Effects](008-isolation-of-side-effects.md)

## Future Revisions

- If per-tenant resource quotas become necessary (beyond per-operation limits), define a supplementary ADR for quota management that builds on this one.
- If the platform introduces streaming responses (e.g., large exports via chunked transfer), define how streaming interacts with bounded operations — streaming may satisfy the "no unbounded result set" rule if backpressure is enforced.
- If operational data reveals that static limits are insufficient (some operations need dynamic bounds based on system load), evaluate adaptive limiting strategies without violating the "explicit and declared" requirement.
