# ADR-005: Explicit Over Implicit Failure

## Status

Accepted

## Context

A system that silently degrades is harder to debug, harder to trust, and more dangerous than one that crashes visibly. Silent failures manifest as data corruption, inconsistent state, partial writes, and bugs that surface far from their origin — often in production, often affecting customers.

Previous ADRs establish that the system defaults to denial (ADR-003) and that boundaries are impermeable (ADR-004). Both assume that violations are surfaced, not swallowed. Without an explicit principle governing failure behavior, individual developers must decide case-by-case whether to fail loudly or degrade gracefully — leading to inconsistent behavior across the codebase.

Constraints:

- Enterprise product — silent data corruption has legal, financial, and reputational consequences.
- Multi-tenant — a silent failure in one tenant's context could contaminate another's data.
- Modular monolith — failures in one module must not silently propagate incorrect state to others.

Architectural goals affected: correctness, debuggability, data integrity, operational confidence.

## Decision

The platform treats silent failure as a defect. Operations succeed completely or fail explicitly — there is no middle ground where partial results are returned without clear indication of failure.

Five invariants govern failure behavior:

1. **Fail fast.** Invalid state is detected and rejected at the earliest possible point. Validation does not defer to later stages what can be caught now.

2. **Fail loudly.** Every failure produces a visible signal — an exception, an error response, a log entry at error level. No failure is swallowed, caught-and-ignored, or reduced to a warning when it represents incorrect behavior.

3. **Fail atomically.** Operations that cannot complete fully leave no partial side effects. The system is never in a state where "half the work" was done and the other half silently didn't happen.

4. **Misconfiguration is a crash.** If the system cannot determine its own correctness (missing settings, invalid plugin registration, incompatible state), it refuses to start or refuses to process the request. Runtime discovery of configuration errors is a bug.

5. **Client input never determines system state.** Client-provided data is never trusted to set system-controlled fields (ownership, permissions, timestamps, internal status). The system derives these values from its own context. If client input attempts to influence system-controlled state, it is either ignored or rejected — never silently accepted.

## Rationale

Benefits:

- Bugs surface at development time or deployment time, not in production under load.
- Debugging is straightforward — the failure is visible where it occurred, not downstream.
- Data integrity is preserved — partial writes don't corrupt state.
- Operational confidence — if the system is running, it believes it is correctly configured.

Tradeoffs:

- The system is less "forgiving" — minor issues that could be worked around will instead halt the operation.
- Startup time may increase if configuration validation is thorough.
- Developers must handle error paths explicitly rather than relying on silent fallbacks.

Assumptions:

- Failing visibly is cheaper than debugging silent corruption.
- Most "graceful degradation" in business applications masks bugs rather than providing genuine resilience.
- The deployment pipeline catches startup failures before they reach production.

Risks:

- Overly strict validation could reject operations that are technically safe, frustrating users.
- If error reporting is poor (loud but uninformative), the principle creates noise without aiding resolution.

## Alternatives Considered

**Graceful degradation by default** — operations do their best, return partial results, log warnings, and continue.

Rejected because:

- "Best effort" in a multi-tenant system means one tenant's partial result could be another tenant's data leak.
- Warnings are ignored in practice — they accumulate until the log is noise.
- Partial results require the caller to understand what's missing, shifting complexity to every consumer.

**Fail-fast for writes, best-effort for reads** — writes are strict, reads tolerate missing data and return what's available.

Rejected because:

- A read that silently omits data due to an internal error is indistinguishable from "the data doesn't exist" — the caller cannot make correct decisions.
- Contradicts ADR-004 — a boundary enforcement failure on a read should deny, not return partial results.

## Consequences

### Positive

- Data corruption from partial operations is architecturally prevented.
- Configuration errors are caught at deploy time, not discovered in production.
- Every failure has a clear signal — no "ghost bugs" that require log archaeology.
- Consistent failure behavior across the codebase — developers know what to expect.

### Negative

- Operations that could "mostly work" will instead fail entirely until the root cause is fixed.
- More upfront validation code is required at system boundaries.
- Startup validation adds deployment-time checks that must be maintained.

### Risks

- If error messages are poor, loud failures become loud confusion.
- Strict atomicity may require transaction management in places where it wasn't previously needed.
- In rare cases, failing an entire batch because of one bad item may be operationally undesirable — these cases must be explicitly designed as "partial with declared failures," not silent degradation.

## Mandatory Rules

- No operation may return a success response while having silently skipped work or produced partial results.
- Exceptions must not be caught and ignored without an explicit, documented justification in the code.
- Configuration errors must prevent startup or request processing — they must never be silently defaulted around.
- Write operations must be atomic — either all side effects are committed or none are.
- Plugin/hook failures must abort the operation, not be swallowed to allow the "main path" to continue.
- System-controlled fields (ownership, timestamps, status, permissions) must be derived server-side. Client-provided values for these fields must be ignored or rejected.

## Allowed Changes

- Defining specific "partial success" semantics for bulk operations, provided each item's success or failure is explicitly reported to the caller (no silent omissions).
- Adding circuit-breaker patterns for external dependencies, provided the circuit-open state is an explicit error, not a silent empty result.
- Relaxing startup validation for optional/non-critical features, provided the feature is visibly disabled (not silently broken).

## Forbidden Changes

- Catching exceptions without re-raising or producing an equivalent error signal.
- Returning HTTP 2xx when the operation did not fully succeed.
- Logging a failure as a warning and continuing as if it didn't happen.
- Defaulting missing configuration values at runtime without explicit declaration in settings.
- Allowing plugin failures to be silently skipped.
- Allowing client input to set system-controlled state (e.g., `tenant_id`, `created_by`, `is_admin`).

## Validation Criteria

- No bare `except: pass` or `except Exception: pass` patterns exist in the codebase (enforceable via linting).
- Every write endpoint either commits all changes or rolls back entirely — no partial state observable after an error.
- Startup with invalid or missing required configuration results in a process exit, not a running server with broken behavior.
- Error responses include sufficient context to identify the failure point without requiring log correlation.
- CI can verify: `grep -r "except.*pass" --include="*.py"` returns zero results outside of explicitly annotated exceptions.
- Serializers for write operations exclude system-controlled fields from accepted input (enforceable via serializer field inspection in tests).

## Related Documents

- [ADR-001: Modular Monolith Architecture](001-modular-monolith-architecture.md)
- [ADR-002: Convention Over Configuration](002-convention-over-configuration.md)
- [ADR-003: Least Exposure by Default](003-least-exposure-by-default.md)
- [ADR-004: Data Boundary Isolation](004-data-boundary-isolation.md)

## Future Revisions

- If the platform introduces eventual consistency patterns (async operations, event sourcing), revisit atomicity guarantees for cross-module operations.
- If bulk import operations become common, define the explicit "partial success with declared failures" contract as a follow-up ADR.
- If startup validation becomes a deployment bottleneck, evaluate lazy validation for non-critical subsystems without violating the "visibly disabled" requirement.
