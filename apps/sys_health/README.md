# sys_health

Operational health check endpoints for orchestrator probes (Kubernetes, ECS).

## Endpoints

| Path | Purpose | Auth |
|------|---------|------|
| `/health/live/` | Liveness — confirms the process is running | None |
| `/health/ready/` | Readiness — verifies DB and Redis connectivity | None |

## Responses

Both endpoints bypass the standard API envelope and return plain JSON:

```json
// GET /health/live/ -> 200
{"status": "alive"}

// GET /health/ready/ -> 200
{"status": "ready"}

// GET /health/ready/ -> 503
{"status": "unavailable", "errors": {"database": "...", "cache": "..."}}
```
