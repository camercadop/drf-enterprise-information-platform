# Redis Reference

This document describes all Redis keys, streams, and database assignments used by the platform. Each section covers the key pattern, TTL, owning component, and design notes.

## Database Assignments

| DB | Purpose | URL setting |
|----|---------|-------------|
| `0` | Django cache (default) | `REDIS_URL` |
| `1` | Celery broker | `CELERY_BROKER_URL` |

---

## Cache Keys (DB 0)

### Idempotency

| Key Pattern | TTL | Value |
|-------------|-----|-------|
| `idempotency:{user_id}:{idempotency_key}` | Configurable (`IDEMPOTENCY_TTL`, default 24h) | JSON — `{"status": "IN_FLIGHT"}` during processing, full response envelope on completion |

Owner: `core/middleware/idempotency.py`

**Design notes:**
- `user_id` is the authenticated user's PK (UUID).
- `idempotency_key` is the value of the `X-Idempotency-Key` request header.
- The `IN_FLIGHT` sentinel prevents concurrent duplicate requests from racing through simultaneously.

---

### Auth Lockout

| Key Pattern | TTL | Value |
|-------------|-----|-------|
| `auth:lockout:attempts:{email}` | Configurable (`AUTH_LOCKOUT["WINDOW_SECONDS"]`) | Integer — failed attempt count |
| `auth:lockout:locked:{email}` | Configurable (`AUTH_LOCKOUT["LOCKOUT_SECONDS"]`) | `1` — presence indicates lockout |

Owner: `apps/iam_auth/lockout.py`

**Design notes:**
- Both keys are deleted on successful login to reset the lockout state.
- `email` is lowercased before use.

---

### Auth Throttling

| Key Pattern | TTL | Value |
|-------------|-----|-------|
| `throttle_login_ip_{ip}` | Sliding window (DRF `SimpleRateThrottle`) | Request timestamp list |
| `throttle_login_email_{email}` | Sliding window (DRF `SimpleRateThrottle`) | Request timestamp list |

Owner: `apps/iam_auth/throttling.py`

**Design notes:**
- Rates are configured via `AUTH_RATE_LIMIT["IP_RATE"]` (default `10/minute`) and `AUTH_RATE_LIMIT["EMAIL_RATE"]` (default `5/minute`).
- Setting a rate to `"0"` disables that throttle entirely.
- Falls back to IP-based key if no email is present in the request body.

---

### Tenant Settings Catalog

| Key | TTL | Value |
|-----|-----|-------|
| `tenant_settings:merged_catalog` | None (persistent until invalidated) | Dict — merged settings catalog from all installed apps |

Owner: `apps/tenant_settings/catalog.py`

**Design notes:**
- No TTL — the key persists until explicitly deleted via `invalidate_catalog_cache()`.
- Invalidated automatically on `TenantSetting` save/delete signals.
- A missing or stale key causes a full catalog rebuild from disk on next access.

---

### Health Check

| Key | TTL | Value |
|-----|-----|-------|
| `_health_check` | 5s | `"1"` |

Owner: `apps/sys_health/views.py`

**Design notes:**
- Written and immediately read back on every health check request to verify Redis connectivity.

---

## Streams (DB 0)

### Event Bus

| Key | Type | TTL |
|-----|------|-----|
| `sys:eventbus` (configurable via `APP_SYS_EVENTBUS["STREAM_NAME"]`) | Redis Stream | None |

Owner: `apps/sys_eventbus/`

**Design notes:**
- Messages are appended via `XADD` by the publisher and consumed via `XREADGROUP` by the Celery beat poller.
- The consumer group is created automatically with `XGROUP CREATE ... MKSTREAM` if absent.
- Processed message IDs are tracked in PostgreSQL (`ProcessedEvent`) for idempotency — not in Redis.
- Failed messages are written to the `DeadLetterEvent` PostgreSQL table, not to a Redis DLQ.

---

## JWT Blacklisting

JWT token blacklisting is handled by `djangorestframework-simplejwt` and stored in **PostgreSQL** (`OutstandingToken` / `BlacklistedToken` tables) — not in Redis.
