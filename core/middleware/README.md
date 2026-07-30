# Core Middleware

Platform-level middleware that applies cross-cutting concerns across all requests.

## Rate Limit Middleware

`BaseRateLimitMiddleware` is an abstract base class that handles all common middleware plumbing: enabled check, view opt-out, skip paths, key building, and throttle raising. Concrete subclasses implement the `is_rate_limited(key, count, window)` method with a specific algorithm.

`FixedWindowRateLimitMiddleware` is the built-in implementation using a fixed-window algorithm backed by Redis.

### Extending

To add a new algorithm, subclass `BaseRateLimitMiddleware` and override `is_rate_limited`:

```python
from core.middleware.rate_limit import BaseRateLimitMiddleware

class SlidingWindowRateLimitMiddleware(BaseRateLimitMiddleware):
    def is_rate_limited(self, key: str, count: int, window: int) -> bool:
        ...
```

Then register it in `MIDDLEWARE` instead of `FixedWindowRateLimitMiddleware`.

### Configuration

Set `APP_RATE_LIMIT` in Django settings:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ENABLED` | `bool` | `False` | Enable or disable rate limiting globally |
| `DEFAULT_RATE` | `str` | `"10/minute"` | Default rate limit in `{count}/{period}` format |
| `SKIP_PATHS` | `list[str]` | `[]` | Path prefixes that are exempt from rate limiting |
| `USE_BOUNDARY_SCOPE` | `bool` | `False` | When enabled, scope rate limit keys by boundary scope |

Supported rate periods: `second`, `minute`, `hour`, `day`.

### View-Level Opt-Out

Any viewset can disable rate limiting by setting `rate_limit_enabled = False` on the class:

```python
class MyViewSet(BaseViewSet):
    rate_limit_enabled = False
```

### Boundary Scope

When `USE_BOUNDARY_SCOPE` is `True`, rate limit keys include the boundary scope identifier (from `get_bound_scope()`). This ensures rate limits are scoped per tenant when boundary scoping is active. When disabled (the default), keys are scoped only by user ID or client IP.

### Key Format

- With boundary scope: `rate_limit:{scope}:{ident}:{path}`
- Without boundary scope: `rate_limit:{ident}:{path}`

Where `ident` is `user:{pk}` for authenticated requests or `ip:{client_ip}` for unauthenticated requests.

### Error Handling

When a request exceeds the rate limit, the middleware raises `ThrottlingError`, which is handled by the custom exception handler and returns a 429 response with a `Retry-After` header indicating how many seconds the client should wait before retrying. The value is the remaining TTL of the rate limit key in Redis, falling back to the full window duration if unavailable.