# ADR-011: Uniform Interface Contract

## Status

Proposed

## Context

The platform exposes a REST API consumed by multiple clients — frontends, integrations, and potentially third-party consumers. Each endpoint is built by different developers at different times. Without a governing principle, interfaces diverge: one endpoint returns errors as a flat string, another as a nested object; one uses `snake_case`, another `camelCase`; one paginates with `offset/limit`, another with cursors; one wraps responses in an envelope, another returns raw data.

Interface inconsistency has compounding costs:

- Clients must learn each endpoint's idiosyncrasies individually — no knowledge transfers between endpoints.
- Shared client libraries (error handling, pagination helpers) cannot be written because the contract varies.
- Documentation becomes essential for every endpoint because behavior is unpredictable.
- Integration testing is more complex — each endpoint has its own shape to assert against.

Previous ADRs establish constraints that demand uniformity:

- ADR-002 (Convention Over Configuration) requires that common concerns have platform-level defaults — the API contract is the most visible common concern.
- ADR-007 (Single Source of Truth) requires that knowledge is defined once — the API contract shape is knowledge that should not be redefined per endpoint.
- ADR-005 (Explicit Over Implicit Failure) requires consistent error signaling — which demands a uniform error format.

Constraints:

- Enterprise product — API consumers expect professional, predictable interfaces.
- Multi-tenant — the same API serves all tenants; per-tenant interface variations are not acceptable.
- Evolvability — the contract must accommodate new resources without breaking existing patterns.

Architectural goals affected: developer experience, consistency, maintainability, client predictability.

## Decision

All external-facing interfaces follow the same structural rules. A consumer who learns one endpoint can predict the shape, behavior, and conventions of any other endpoint in the system.

Three invariants govern this principle:

1. **One envelope, everywhere.** Every API response — success or failure — uses the same top-level structure. The consumer never guesses which shape to parse. The envelope is the contract; the payload varies.

2. **One set of conventions, everywhere.** Naming (URL patterns, field names, query parameters), pagination mechanics, filtering syntax, ordering syntax, and error taxonomy are identical across all resources. No endpoint invents its own conventions.

3. **Predictability over optimization.** If a uniform approach is slightly less optimal for a specific endpoint but preserves predictability across the API, uniformity wins. Per-endpoint optimizations that break the contract are forbidden.

## Rationale

Benefits:

- Clients build one integration pattern and reuse it across all endpoints — reduced integration cost.
- Shared client libraries (SDK, error handlers, pagination utilities) are possible because the contract is stable.
- New endpoints are immediately usable by existing clients without learning new conventions.
- Documentation can describe the contract once and reference it from every endpoint — per-endpoint docs only describe the payload.

Tradeoffs:

- Some endpoints may be slightly less optimal than a bespoke design would allow (e.g., a resource that doesn't need pagination still returns paginated structure).
- The uniform contract must be designed upfront and is expensive to change once clients depend on it.
- Edge cases (file downloads, streaming, webhooks) may require documented exceptions to the envelope.

Assumptions:

- The API is primarily consumed by programmatic clients (frontends, integrations) that benefit from predictability over flexibility.
- The set of structural conventions (envelope, pagination, filtering, errors) is small and stable.
- Edge cases that cannot fit the uniform contract are rare and can be explicitly documented as exceptions.

Risks:

- The uniform contract being too rigid for future requirements, forcing awkward workarounds.
- Exceptions accumulating until the "uniform" contract is uniform in name only.
- The contract being designed too early, before enough endpoints exist to validate it.

## Alternatives Considered

**Per-resource contract design** — each resource defines its own response shape, pagination strategy, and error format based on its specific needs.

Rejected because:

- Violates ADR-002 — common concerns should have platform defaults, not per-resource decisions.
- Violates ADR-007 — the "how responses are shaped" knowledge is duplicated and potentially contradictory across resources.
- Client integration cost scales linearly with the number of resources.

**GraphQL as the uniform interface** — adopt GraphQL, which provides structural uniformity by design (single endpoint, typed schema, uniform query language).

Rejected because:

- Technology choice, not an architectural principle — this ADR governs the principle regardless of the transport mechanism.
- Does not eliminate the need for conventions (error handling, pagination patterns, naming) — GraphQL APIs still need uniform conventions within their schema.
- Adds infrastructure complexity disproportionate to current needs.

## Consequences

### Positive

- API consumers learn the contract once and apply it everywhere — reduced cognitive load and integration time.
- Shared client utilities (pagination helpers, error parsers) work across all endpoints.
- New resources are immediately predictable to existing consumers.
- API documentation is structured as "contract + per-resource payload" rather than "per-endpoint everything."

### Negative

- Contract rigidity — changing the envelope or conventions is a breaking change for all consumers simultaneously.
- Some resources carry structural overhead that their specific use case doesn't require (e.g., pagination metadata on a singleton resource).
- Edge cases require explicit, documented exceptions — each exception weakens the uniformity guarantee.

### Risks

- The contract ossifying prematurely before enough real-world usage validates it.
- Exception creep — too many "special cases" eroding the uniformity until it's meaningless.
- Over-engineering the contract for hypothetical future needs rather than current requirements.

## Mandatory Rules

- Every API response must use the platform's standard envelope structure — no endpoint may define its own top-level response shape.
- Error responses must follow the platform's error taxonomy and structure — no endpoint may invent its own error format.
- Pagination, filtering, and ordering must use the platform's standard mechanisms and query parameter conventions — no endpoint may implement its own variants.
- URL patterns and field naming must follow the platform's declared conventions — no endpoint may deviate without an explicit, documented exception.
- Exceptions to the uniform contract (file downloads, streaming, webhooks) must be explicitly documented and minimized.

## Allowed Changes

- Evolving the contract (adding optional fields to the envelope, extending the error taxonomy) in backward-compatible ways.
- Defining new convention categories (e.g., bulk operation request format) that apply uniformly to all endpoints of that type.
- Documenting explicit exceptions for operations that structurally cannot fit the envelope (binary responses, server-sent events).
- Versioning the contract if breaking changes become necessary — provided all endpoints within a version are uniform.

## Forbidden Changes

- Individual endpoints defining their own response envelope, error format, or pagination mechanism.
- Naming convention deviations (mixing `snake_case` and `camelCase`, inconsistent URL patterns) without a documented, platform-wide exception.
- Returning success responses (2xx) with a structure that differs from the standard envelope.
- Silently deviating from the contract — any exception must be documented and justified.

## Validation Criteria

- Every API endpoint returns responses matching the platform's envelope schema — enforceable by integration tests or response middleware validation.
- Error responses from any endpoint are parseable by a single, shared error-handling utility — verifiable by using one error parser across all endpoint tests.
- Pagination query parameters and response metadata are identical across all collection endpoints — enforceable by shared test utilities.
- URL patterns follow the declared naming convention — enforceable by URL configuration inspection or linting.
- No undocumented exceptions to the contract exist — verifiable by maintaining an explicit exception registry.

## Related Documents

- [ADR-002: Convention Over Configuration](002-convention-over-configuration.md)
- [ADR-005: Explicit Over Implicit Failure](005-explicit-over-implicit-failure.md)
- [ADR-007: Single Source of Truth](007-single-source-of-truth.md)

## Future Revisions

- If the number of documented exceptions grows beyond a threshold (suggesting the contract is too rigid), revisit the envelope design to accommodate the common exception patterns.
- If the platform introduces non-REST interfaces (WebSocket, gRPC), define how the uniformity principle applies to those transports — the principle may require a separate contract per transport, each internally uniform.
- If API versioning becomes necessary, define how multiple contract versions coexist without fragmenting the uniformity guarantee within each version.
