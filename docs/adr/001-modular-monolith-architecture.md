# ADR-001: Modular Monolith Architecture

## Status

Accepted

## Context

The platform needs a deployment architecture that supports multiple business domains (authentication, tenants, users, and future modules). The team is small, no domain has demonstrated a need for independent scaling, and fast iteration is a priority.

Constraints:

- Small team — no capacity to operate distributed infrastructure.
- Enterprise product — reliability and consistency matter more than independent deployability.
- Multiple domains — clear boundaries are needed to prevent coupling as the codebase grows.

Architectural goals affected: deployability, evolvability, operational simplicity.

## Decision

Adopt a modular monolith: a single codebase deployed as one unit, with domain modules isolated under `apps/` and shared infrastructure in `core/`. Communication between modules is in-process via Python imports through well-defined interfaces.

## Rationale

Benefits:

- Single deployment unit eliminates distributed system complexity (no distributed transactions, service discovery, or inter-service networking).
- Cross-domain features are atomic — single DB transaction, single deploy.
- Clean module boundaries provide the discipline of microservices without the operational cost.
- Appropriate for the current team size and product stage.

Tradeoffs:

- Module extraction requires effort when the need arises — but clean boundaries minimize that cost.
- All domains share a failure domain — a crash affects the entire platform.

Assumptions:

- No domain will require independent scaling in the near term.
- The team will remain small enough that a shared codebase does not create coordination bottlenecks.

Risks:

- If the assumption about team size or scaling needs proves wrong earlier than expected, migration to microservices under pressure is costly.

## Alternatives Considered

**Microservices from day one** — rejected because:

- Introduces distributed system complexity (eventual consistency, saga patterns, API versioning) without proven need.
- Requires significant infrastructure (API gateway, service discovery, per-service databases, distributed tracing, per-service CI/CD).
- Team autonomy benefit does not materialize with a small team.

## Consequences

### Positive

- Operational simplicity — one deployment, one database, one CI pipeline.
- Fast iteration — changes across domains ship together atomically.
- Evolvability — module boundaries allow future extraction when justified.

### Negative

- All domains scale together — cannot independently scale a single module.
- Shared deployment — a change in one module requires redeploying the entire platform.

### Risks

- Coupling creep — without enforced layering rules, modules may develop implicit dependencies.
- Monolith growth — without periodic review, the codebase may become difficult to navigate.

## Mandatory Rules

- Each domain module lives under `apps/` as a self-contained Django app (own models, serializers, views, URLs, tests).
- Shared infrastructure lives in `core/`.
- Inter-module communication is in-process only (Python imports) — no network calls between modules within the monolith.

## Allowed Changes

- Adding new domain modules under `apps/`.
- Extracting a module into an independent service if a concrete need is demonstrated (independent scaling, team ownership, fault isolation).
- Running async workers (Celery) as separate processes sharing the same codebase.

## Forbidden Changes

- Direct cross-app database FK references without explicit design review.
- Deploying individual `apps/` modules as separate services without completing the full extraction process (own DB, API contract, event-based communication).

## Validation Criteria

- All domain logic lives under `apps/`, not scattered in `core/` or `config/`.
- The platform is deployed as a single unit (one Dockerfile, one `docker-compose` service for the web process).
- Each app under `apps/` has its own models, views, serializers, URLs, and tests (self-contained structure).

## Future Revisions

- If a domain demonstrates a need for independent scaling or fault isolation, revisit this decision and document the extraction plan as a new ADR.
- If the team grows to multiple squads owning different domains, evaluate whether service boundaries should align with team boundaries.
