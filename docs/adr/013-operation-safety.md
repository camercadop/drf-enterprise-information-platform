# ADR-013: Operation Safety

## Status

Proposed

## Context

Distributed systems experience retries. Networks drop packets, clients time out and resubmit, background task queues deliver messages more than once, and users double-click buttons. When a write operation is not safe to retry, each of these common scenarios becomes a source of data corruption: duplicate records, double-applied state transitions, repeated side effects.

The platform operates in an environment where retries are inevitable:

- HTTP clients retry on timeout — the server may have processed the request but the response was lost.
- Background task queues guarantee at-least-once delivery, not exactly-once.
- Users submit forms multiple times when the UI is slow to respond.
- Infrastructure failures (database connection drops mid-transaction) trigger automatic reconnection and retry.

Previous ADRs establish constraints that make retry safety architecturally necessary:

- ADR-005 (Explicit Over Implicit Failure) requires atomicity — but atomicity alone does not prevent a successfully committed operation from being applied again on retry.
- ADR-008 (Isolation of Side Effects) requires side effects at declared boundaries — but a retried operation that re-triggers side effects (duplicate notifications, double charges) violates the consumer's expectations even if each individual execution is correct.
- ADR-010 (Bounded Operations) ensures operations have limits — but a retried operation that creates a duplicate record is not an unbounded operation; it is a correctness violation that bounds cannot prevent.

Constraints:

- Enterprise product — duplicate financial transactions, duplicate records, or duplicate notifications have business consequences.
- Multi-tenant — a retry that creates duplicate data in one tenant's context pollutes their data integrity.
- At-least-once delivery — the platform cannot rely on exactly-once guarantees from infrastructure.

Architectural goals affected: correctness, data integrity, operational resilience, consumer trust.

## Decision

Write operations are designed to be safe to retry. Executing the same logical operation more than once produces the same outcome as executing it exactly once. The system tolerates duplicate submissions without producing duplicate effects.

Three invariants govern this principle:

1. **Same request, same outcome.** A write operation that is submitted multiple times with the same intent produces the same final state as a single submission. The second execution either recognizes the duplicate and returns the existing result, or the operation is naturally idempotent by design (e.g., "set X to 5" rather than "increment X by 1").

2. **State transitions are guarded.** Operations that move a resource from one state to another validate the current state before applying the transition. A transition that has already been applied is recognized and handled gracefully — not applied again.

3. **Side effects are deduplicated at the boundary.** Side effects triggered by an operation (per ADR-008) are protected against duplicate execution. A retried operation does not re-send a notification, re-emit an event, or re-trigger an external call if the side effect has already been executed for that logical operation.

## Rationale

Benefits:

- Network retries, client resubmissions, and queue redeliveries are safe — they do not corrupt data.
- Operational resilience — the system can aggressively retry failed operations without fear of duplication.
- Consumer trust — clients can implement simple retry logic without complex deduplication on their side.
- Background task processing is simplified — at-least-once delivery is sufficient; exactly-once is not required.

Tradeoffs:

- Idempotency mechanisms add complexity — deduplication keys, state guards, and side effect tracking require design and storage.
- Not all operations are naturally idempotent — some require explicit mechanisms (idempotency keys, unique constraints) to achieve safety.
- Storage overhead for tracking processed operations (idempotency key records, processed event IDs).

Assumptions:

- At-least-once delivery is the baseline guarantee from infrastructure (HTTP, task queues, event streams).
- The cost of idempotency mechanisms is lower than the cost of duplicate data and its downstream consequences.
- Most write operations can be made idempotent through design choices (state guards, unique constraints, upsert semantics) without dedicated deduplication infrastructure.

Risks:

- Idempotency key storage growing unboundedly if not managed with retention policies (mitigated by ADR-010 — bounded operations applies to storage too).
- False deduplication — incorrectly identifying a legitimate new operation as a retry of a previous one.
- Complexity of deduplicating side effects across async boundaries where the side effect executor is separate from the primary operation.

## Alternatives Considered

**Exactly-once delivery infrastructure** — invest in infrastructure that guarantees each message/request is processed exactly once, eliminating the need for application-level idempotency.

Rejected because:

- Exactly-once delivery is a theoretical impossibility in distributed systems — all practical implementations are at-least-once with deduplication, which is what this ADR mandates at the application level.
- Relying on infrastructure guarantees that may not hold under failure conditions is a silent failure waiting to happen (violates ADR-005).
- Even with "exactly-once" infrastructure, client-side retries (user double-clicks, HTTP retries) still produce duplicates at the application boundary.

**Client-side deduplication only** — require clients to implement their own deduplication logic; the server processes every request as unique.

Rejected because:

- Shifts complexity to every consumer — each client must independently solve the same problem.
- Not all clients are under the platform's control — third-party integrations may not implement deduplication.
- Server-side state is the only reliable place to detect duplicates — the server knows what has already been processed.

## Consequences

### Positive

- Retries at any layer (network, client, queue) are safe — no duplicate data or effects.
- Background task processing is resilient — at-least-once delivery is sufficient without complex exactly-once infrastructure.
- Client integration is simpler — retry logic does not require client-side deduplication.
- Operational confidence — aggressive retry policies can be used for reliability without risking correctness.

### Negative

- Design complexity — every write operation must consider its idempotency strategy during design.
- Storage overhead — idempotency keys and deduplication records require storage and retention management.
- Not all operations are naturally idempotent — some require explicit mechanisms that add code and infrastructure.

### Risks

- Idempotency key collisions or incorrect scoping causing false deduplication (legitimate operations rejected as duplicates).
- Deduplication record retention becoming a storage concern if not bounded (per ADR-010).
- Side effect deduplication across async boundaries being incomplete — a retried operation that does not re-trigger its side effects may leave the system in an inconsistent state if the original side effect also failed.

## Mandatory Rules

- Write operations must be safe to execute more than once with the same logical intent — duplicate submissions must not produce duplicate state changes.
- State transitions must validate current state before applying — a transition that has already occurred must be recognized, not blindly reapplied.
- Side effects attached to write operations (per ADR-008) must have deduplication protection — a retried operation must not re-trigger side effects that have already executed for that logical operation.
- Operations that are not naturally idempotent must implement an explicit idempotency mechanism (idempotency keys, unique constraints, conditional writes).
- Duplicate detection must produce an explicit, informative response — not a silent success that hides the fact that the operation was already processed.

## Allowed Changes

- Choosing different idempotency strategies per operation type (natural idempotency, idempotency keys, unique constraints, conditional writes) based on the operation's characteristics.
- Defining retention policies for idempotency/deduplication records — provided the retention window exceeds the maximum expected retry window.
- Implementing side effect deduplication at the side effect boundary (per ADR-008) rather than at the primary operation level, when the side effect executor has its own deduplication capability.
- Accepting that some side effects (logging, metrics) are safe to duplicate and exempting them from deduplication requirements.

## Forbidden Changes

- Write operations that produce duplicate records, duplicate state transitions, or duplicate side effects when retried.
- State transitions that apply blindly without checking current state (e.g., "increment" without guard vs. "set to X if currently Y").
- Silently succeeding on duplicate detection without indicating to the caller that the operation was already processed.
- Relying solely on client-side deduplication for correctness — the server must be the authority on what has been processed.

## Validation Criteria

- Every write endpoint, when called twice with the same logical request, produces the same final state and does not create duplicate records — verifiable by integration tests that submit each write operation twice.
- State transition operations reject or gracefully handle attempts to apply an already-completed transition — verifiable by testing transition replay.
- Side effects (notifications, events, external calls) are not duplicated when the triggering operation is retried — verifiable by testing retry scenarios with side effect observation.
- Duplicate detection returns an explicit response distinguishable from a first-time success — verifiable by asserting response differences between first and duplicate submissions.
- Background tasks produce correct results when delivered more than once — verifiable by executing each task type twice with the same payload.

## Related Documents

- [ADR-005: Explicit Over Implicit Failure](005-explicit-over-implicit-failure.md)
- [ADR-008: Isolation of Side Effects](008-isolation-of-side-effects.md)
- [ADR-010: Bounded Operations](010-bounded-operations.md)

## Future Revisions

- If the platform introduces event sourcing, revisit how idempotency interacts with event replay — event streams have their own deduplication semantics.
- If idempotency key storage becomes a scaling concern, evaluate distributed deduplication strategies (bloom filters, time-windowed key stores).
- If cross-service operations emerge (saga patterns), define how idempotency applies to multi-step distributed operations where individual steps may be retried independently.
