# Error Codes

Reference catalog of all machine-readable error codes returned by the API. This document is for API consumers — for implementation guidance, see [Error Handling guideline](guidelines/error-handling.md).

---

## Response Format

All errors follow the standard envelope:

```json
{
  "status": "ERROR",
  "code": "<error_code>",
  "data": "Message string or field error dict"
}
```

The `code` field is always a snake_case string. Clients should switch on `code` for programmatic handling, not on the human-readable message in `data`.

---

## Global Codes

These codes can be returned by any endpoint.

| Code | HTTP Status | Meaning | Client Action |
|------|-------------|---------|---------------|
| `validation_error` | 400 | Request body failed validation or data integrity constraint violated (no DB details exposed) | Check `data` for field-specific errors |
| `authentication_error` | 401 | Missing or invalid credentials | Re-authenticate (login or refresh) |
| `permission_denied` | 403 | Authenticated but not authorized | User lacks required role or membership |
| `not_found` | 404 | Resource does not exist or is soft-deleted | Verify the resource ID and tenant context |
| `conflict` | 409 | Operation conflicts with current resource state | Check current state before retrying |
| `throttling_error` | 429 | Rate limit exceeded | Retry after backoff |
| `server_error` | 500 | Unexpected server failure (generic, no internal details exposed) | Retry; report if persistent |

---

## Endpoint-Specific Codes

Each endpoint documents its own error codes in the OpenAPI schema. Refer to the generated API documentation for per-endpoint error responses.

---

## Field Validation Errors

When serializer validation fails, `data` contains a dict mapping field names to error lists:

```json
{
  "status": "ERROR",
  "code": "required",
  "data": {
    "name": ["This field is required."],
    "email": ["Enter a valid email address."]
  }
}
```

Common field-level codes:

| Code | Meaning |
|------|---------|
| `required` | Field is missing |
| `blank` | Field is empty string |
| `null` | Field is null when not allowed |
| `invalid` | Value format is wrong |
| `unique` | Value already exists |
| `max_length` | Value exceeds maximum length |
| `min_length` | Value is below minimum length |

---

## Handling Unknown Codes

New codes may be introduced as the API evolves. Clients should:

1. Handle known codes explicitly
2. Fall back to the HTTP status code for unknown codes (4xx = client error, 5xx = server error)
3. Display the `data` message to the user as a last resort
