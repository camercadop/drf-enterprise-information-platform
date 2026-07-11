# ADR-009: Auditability by Design

## Status

Accepted

## Context

The platform manages multi-tenant enterprise data where state changes have legal, financial, and operational consequences. When something goes wrong — a permission was revoked, a record was deleted, a configuration was changed — the first question is always: who did this, when, and why?

Without a governing principle, auditability becomes an afterthought — bolted on inconsistently, missing for some operations, and unreliable for the ones that matter most. Developers make case-by-case decisions about what to log, where to record it, and how much context to preserve. The result is gaps that only become visible during incident investigation or compliance audits.

Previous ADRs establish constraints that auditability depends on:

- ADR-004 requires that cross-boundary access is auditable — but does not define what "auditable" means system-wide.
- ADR-005 requires that failures are explicit — but a successful operation that leaves no trace is equally problematic when investigating an incident.
- ADR-008 establishes that side effects (including audit recording) live at declared lifecycle boundaries — giving auditability predictable, reliable attachment points.

Constraints:

- Enterprise product — regulatory and contractual obligations may require demonstrating who accessed or modified data.
- Multi-tenant — an audit trail must be scoped to its boundary; one tenant's audit records must not leak to another.
- Operational reality — production incidents must be diagnosable from recorded context, not by reproducing the conditions.

Architectural goals affected: accountability, debuggability, compliance, operational confidence.

## Decision

Every meaningful state change in the system is traceable after the fact. The system is explainable — not just correct. Operations carry context about who triggered them, from where, and within what boundary, and this context is preserved as part of the system's correctness guarantee.

Three invariants govern auditability:

1. **Operations are never anonymous.** Every operation that changes state has a declared actor — a user, a system process, or an automated trigger. There is no "it just happened." Even system-initiated actions (migrations, scheduled tasks, background jobs) have a declared identity.

2. **Context flows through the entire operation.** The identity, tenant, and action context established at the entry point is available at every layer of the call stack — including background tasks that execute asynchronously. Context is not reconstructed or guessed; it is propagated from the origin.

3. **The audit trail is not optional.** Recording state changes is part of the system's correctness contract, not a logging convenience. An operation that succeeds but leaves no trace is as defective as one that fails silently (per ADR-005). The audit mechanism participates in the operation's lifecycle as a declared side effect (per ADR-008).

## Rationale

Benefits:

- Production incidents are diagnosable from recorded context — no need to reproduce conditions.
- Compliance questions ("who accessed this data?", "who changed this permission?") are answerable from the system itself.
- Cross-boundary access (ADR-004) has a verifiable record, fulfilling that ADR's auditability requirement.
- Accountability is structural — not dependent on developers remembering to add logging.

Tradeoffs:

- Every state-changing operation carries the overhead of audit recording — storage, write amplification, and lifecycle hook execution.
- The audit trail itself becomes data that must be governed — retention, access control, and boundary isolation apply to it.
- Context propagation adds a threading concern — every async boundary (background tasks, queues) must explicitly carry context forward.

Assumptions:

- The cost of recording audit data is acceptable relative to the cost of not having it during an incident or audit.
- The platform's lifecycle hooks (ADR-008) provide reliable attachment points for audit recording.
- Audit records are append-only — they are never modified or deleted by application logic.

Risks:

- Audit storage growing unboundedly if retention policies are not defined.
- Context propagation breaking silently at async boundaries — the operation succeeds but the audit record has incomplete context.
- Over-auditing — recording so much that the signal is lost in noise, making the audit trail useless in practice.

## Alternatives Considered

**Selective auditing — only audit "important" operations** — developers decide per-operation whether audit recording is warranted.

Rejected because:

- "Important" is subjective and changes over time — what seems unimportant today becomes critical during an incident.
- Gaps in the audit trail are invisible until you need the missing record.
- Contradicts the principle that auditability is a correctness guarantee, not a convenience.

**Application-level logging as audit trail** — rely on structured logging (log lines with context) rather than a dedicated audit mechanism.

Rejected because:

- Logs are ephemeral — retention is typically short, and log infrastructure is optimized for debugging, not compliance.
- Log format and content are inconsistent across the codebase unless heavily standardized.
- Logs are not queryable as structured data — answering "who changed X between date A and date B" requires log parsing, not a query.
- Logs do not participate in the operation's transaction — a log line can be written for an operation that was subsequently rolled back.

## Consequences

### Positive

- Every state change is traceable to an actor, a time, and a boundary context.
- Incident investigation starts from recorded facts, not from reproduction attempts.
- Compliance and regulatory questions are answerable from system data.
- Cross-boundary access auditing (ADR-004) is fulfilled by a system-wide mechanism rather than per-boundary ad-hoc solutions.

### Negative

- Write amplification — every state change produces at least one additional write (the audit record).
- Storage growth — audit data accumulates and requires retention management.
- Context propagation complexity — async boundaries must explicitly carry context, adding a concern to every background task or queue consumer.

### Risks

- Audit records themselves becoming a data leak vector if not properly boundary-scoped.
- Context propagation failing silently at async boundaries, producing audit records with incomplete information.
- Audit storage becoming a performance bottleneck if not managed with appropriate retention and archival strategies.

## Mandatory Rules

- Every operation that changes persistent state must produce an audit record identifying the actor, the action, the target, and the boundary context.
- No operation may execute without a declared actor. System-initiated operations must use a declared system identity, not null or anonymous.
- Request context (identity, tenant, action) must be propagated through the entire call stack, including across async boundaries (background tasks, deferred execution).
- Audit recording must be attached at declared lifecycle boundaries (per ADR-008) — not implemented inline in business logic.
- Audit records are append-only within the application layer. Application code must not modify or delete audit records.

## Allowed Changes

- Defining retention policies that archive or purge audit records after a defined period — provided purging is itself audited.
- Varying the detail level of audit records by operation category (e.g., more detail for destructive operations, less for routine reads) — provided the minimum fields (actor, action, target, boundary, timestamp) are always present.
- Introducing async audit recording for non-critical operations — provided the audit record is guaranteed to eventually be written and context is fully propagated.
- Extending audit records with additional context fields as operational needs evolve.

## Forbidden Changes

- Allowing state-changing operations to execute without producing an audit record.
- Allowing operations to execute with an anonymous or null actor.
- Implementing audit recording inline in business logic rather than at lifecycle boundaries.
- Allowing application code to modify or delete existing audit records.
- Dropping context at async boundaries — background tasks must carry the full context of the original trigger.

## Validation Criteria

- Every state-changing endpoint produces an audit record containing at minimum: actor, action, target resource, boundary context, and timestamp.
- No operation in the system can execute with a null or anonymous actor — enforceable by middleware or base class validation.
- Background tasks carry and record the context of the original triggering operation — verifiable by inspecting audit records for async operations.
- Audit records are immutable from the application layer — no update or delete operations exist for audit models.
- Audit recording is attached at lifecycle hooks, not called from within business logic methods — enforceable by architectural tests.

## Related Documents

- [ADR-004: Data Boundary Isolation](004-data-boundary-isolation.md)
- [ADR-005: Explicit Over Implicit Failure](005-explicit-over-implicit-failure.md)
- [ADR-008: Isolation of Side Effects](008-isolation-of-side-effects.md)

## Future Revisions

- If audit storage volume becomes a cost or performance concern, define a tiered retention strategy (hot/warm/cold) without violating append-only semantics.
- If the platform introduces read-auditing requirements (compliance scenarios where data access must be traced), extend this ADR or create a supplementary one — the current scope covers state changes only.
- If context propagation across async boundaries proves unreliable, evaluate infrastructure-level solutions (e.g., correlation IDs in message headers, context-aware task decorators) as mandatory rather than optional.
