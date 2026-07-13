# API Conventions

Client-facing contract for the REST API. This document describes what API consumers can rely on regardless of which endpoint they call.

---

## Base URL

All endpoints are served under `/api/`:

```
/api/auth/...
/api/tenants/...
/api/<domain>/...
```

No version prefix is used currently. If versioning is introduced, it will follow the pattern `/api/v2/...` with the unversioned path continuing to serve the latest stable version during a deprecation window.

---

## URL Structure

| Convention | Example |
|------------|---------|
| Plural resource names | `/api/tenants/`, `/api/memberships/` |
| UUID for resource identifiers | `/api/tenants/<uuid>/` |
| Trailing slash required | `/api/tenants/` (not `/api/tenants`) |
| Domain-grouped routes (tenant-scoped) | `/api/tenants/memberships/` (tenant is implicit from JWT, no ID in URL) |
| Nested routes (parent-child) | `/api/projects/<uuid>/tasks/` (parent ID in URL when not resolvable from context) |
| Hyphenated multi-word paths | `/api/auth/logout-all/` |
| Custom actions as sub-paths | `/api/memberships/<uuid>/deactivate/` |

---

## HTTP Methods and Status Codes

### Standard CRUD

| Action | Method | Success Status | Response Body |
|--------|--------|----------------|---------------|
| List | GET | 200 | Paginated collection |
| Retrieve | GET | 200 | Single resource |
| Create | POST | 201 | Created resource |
| Full update | PUT | 200 | Updated resource |
| Partial update | PATCH | 200 | Updated resource |
| Delete (soft) | DELETE | 204 | No content |

### Partial Update Semantics (PATCH)

- Only fields present in the request body are updated
- Omitted fields remain unchanged
- Sending `null` explicitly clears a nullable field
- Sending `null` on a non-nullable field returns a validation error

### Non-CRUD Actions

| Semantics | Method | Success Status | Example |
|-----------|--------|----------------|---------|
| Action that returns data | POST | 200 | Login, token refresh, password change |
| Side-effect with no response body | POST | 204 | Logout, deactivate |

---

## Content Type

- Request: `application/json`
- Response: `application/json`
- Character encoding: UTF-8

---

## Data Formats

| Type | Format | Example |
|------|--------|---------|
| Identifiers | UUID v4 | `"550e8400-e29b-41d4-a716-446655440000"` |
| Timestamps | ISO 8601 with timezone | `"2024-01-15T10:30:00Z"` |
| Booleans | JSON native or numeric | `true` / `false` / `1` / `0` |
| Null values | JSON native | `null` |
| Field names | snake_case | `"created_at"`, `"is_active"` |

---

## Authentication

All endpoints require authentication unless explicitly marked as public.

### Header

```
Authorization: Bearer <access_token>
```

### Public Endpoints

These do not require the `Authorization` header:

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`

### Token Lifecycle

| Token | Lifetime | Obtained via |
|-------|----------|--------------|
| Access | 30 minutes | Login or refresh |
| Refresh | 7 days | Login or refresh (rotates) |

---

## Response Envelope

All responses are wrapped in a standard envelope.

### Success

```json
{
  "status": "OK",
  "data": { ... }
}
```

### Error

```json
{
  "status": "ERROR",
  "code": "<machine_readable_code>",
  "data": "Human-readable message or field error dict"
}
```

The `code` field is always a snake_case string suitable for programmatic switching. See [Error Codes](error-codes.md) for the full catalog.

---

## Pagination

All list endpoints are paginated. The response shape:

```json
{
  "status": "OK",
  "data": {
    "count": 42,
    "page_size": 10,
    "current_page": 1,
    "total_pages": 5,
    "results": [ ... ]
  }
}
```

### Query Parameters

| Parameter | Default | Max | Description |
|-----------|---------|-----|-------------|
| `page` | 1 | — | Page number |
| `page_size` | 10 | 100 | Items per page |

---

## Filtering, Search, and Ordering

### Filtering

Field-based filtering via query parameters. Available filters are endpoint-specific and documented in the OpenAPI schema.

```
GET /api/tenants/?is_active=true
```

### Search

Full-text search across configured fields. Always uses the `search` query parameter:

```
GET /api/tenants/?search=acme
```

### Ordering

Sort by one or more fields. Prefix with `-` for descending:

```
GET /api/tenants/?ordering=-created_at
GET /api/memberships/?ordering=user__email,-created_at
```

### Field Restrictions

Not every field supports filtering, search, or ordering. Only explicitly declared fields are available for each operation. Unrecognized fields in query parameters are silently ignored.

### Large Filter Sets

When query parameters would exceed URL length limits (2048 characters), endpoints may expose a `POST`-based filter action. This is a read operation despite using POST — it does not create or modify resources. The request body format will be documented per endpoint when available.

---

## Empty Collections

A list endpoint with no matching results returns `200` with an empty `results` array — not `404`:

```json
{
  "status": "OK",
  "data": {
    "count": 0,
    "page_size": 10,
    "current_page": 1,
    "total_pages": 0,
    "results": []
  }
}
```

---

## Soft-Delete Visibility

Soft-deleted records are excluded from responses by default. Authorized users (superusers, tenant admins) can include them:

```
GET /api/tenants/?include_deleted=true
```

---

## Tenant Context

Most endpoints are tenant-scoped. The tenant is resolved from the JWT `tenant_id` claim — clients do not pass it as a query parameter or header. Resources outside the authenticated tenant are invisible (404).

---

## Idempotency

- `GET`, `PUT`, `DELETE` are idempotent
- `POST` is not idempotent by default (repeated calls create duplicate resources)
- Some `POST` endpoints are idempotent by design (e.g., login, logout, deactivate). These are documented individually and safe to retry
- Custom actions (`POST /resource/<id>/action/`) document their idempotency individually
